# -*- coding:utf-8 -*-

import tornado.ioloop as tioloop
import tornado.web as tweb

import xml.etree.ElementTree as et
import pony.orm as orm

import sys
import os

__dir__ = os.path.abspath(os.path.dirname(__file__))

# sys.path.append("/home/concefly/project/git/tornado_connector")

# import connector

# 配置数据库
db = orm.Database('sqlite', 'address_book.sq3', create_db=True)

# 数据库 model
class Person(db.Entity):
	id     = orm.PrimaryKey(int, auto=True)
	name   = orm.Required(str)
	mobile = orm.Optional(str)
	tags   = orm.Set("Tag")
	group  = orm.Required("Group")

class Tag(db.Entity):
	id     = orm.PrimaryKey(int, auto=True)
	name   = orm.Required(str, unique=True)
	people = orm.Set(Person)

class Group(db.Entity):
	id     = orm.PrimaryKey(int, auto=True)
	name   = orm.Required(str, unique=True)
	people = orm.Set(Person)

db.generate_mapping(create_tables=True)

# HTTP 句柄

class base_handler(tweb.RequestHandler):
	def write_xml(self,x):
		if isinstance(x,et.Element):
			x = et.tostring(x,encoding="utf-8")
		self.write(x)
		self.set_header("Content-Type","text/xml")

class MainHandler(base_handler):
	def get(self):
		self.redirect("/static/index.html")

class contacts_handler(base_handler):
	user_field    = ["name","mobile"]
	default_frame = os.path.join(__dir__,"static","frame","contacts_default.xml")
	def get(self):
		if hasattr(self,"default_frame"):
			rows = et.parse(self.default_frame).getroot()
		else:
			rows = et.Element('rows')
		tags = self.get_query_arguments("tag")
		group = self.get_query_argument("group",default=None)
		with orm.db_session:
			if group:
				query = orm.select(p for p in Person if p.group.name==group)
			else:
				query = orm.select(p for p in Person)
			for i in query:
				row = et.Element("row")
				row.set("id",str(i.id))
				if hasattr(self,"user_field"):
					for _cell in self.user_field:
						cell = et.Element("cell")
						cell.text = getattr(i,_cell)
						row.append(cell)
				# group @cell
				cell = et.Element("cell")
				cell.text = i.group.name
				row.append(cell)
				# tag @cell
				cell = et.Element("cell")
				cell.text = ", ".join(list(i.tags.name))
				row.append(cell)
				# 
				rows.append(row)
		self.write_xml(rows)
	def post(self):
		"""POST的参数：
		@group: 组名字符串。后台自动添加不存在的组名。可空，默认为"noclass"。
		@tags: 标签字符串。用逗号分隔，后台自动添加不存在的标签名。可空。
		"""
		if self.get_argument("editing",default=None) != "true":
			return
		ids = self.get_body_argument("ids",default="").split(',')
		res = et.Element("data")
		for _id in ids:
			gr_id = self.get_body_argument("%s_gr_id" %(_id,))
			field = {}
			# 填充group和tags字段
			field["group"] = self.get_body_argument("%s_group" %(_id,),default="")
			field["tags"] = self.get_body_argument("%s_tag" %(_id,),default="")
			if not field['group']:
				field['group'] = "noclass"
			if not field['tags']:
				field['tags'] = ""
			# 填充用户字段
			if hasattr(self,"user_field"):
				for _name in self.user_field:
					field[_name] = self.get_body_argument("%s_%s" %(_id,_name),default="-")
			status = self.get_body_argument("%s_!nativeeditor_status" %(_id,))
			# 写入数据库
			tid = [gr_id]
			with orm.db_session:
				if status=="updated":
					r = Person[gr_id]
					if hasattr(self,"user_field"):
						for k in self.user_field:
							setattr(r, k, field[k])
					# 处理group字段
					# 新建不存在的group
					_group = Group.get(name=field['group'])
					if _group:
						r.group = _group
					else:
						r.group.create(name=field['group'])
					# 处理tags字段
					# 新建不存在的tag
					for tag in field['tags'].split(','):
						if tag:
							_tag = Tag.get(name=tag)
							if _tag:
								r.tags.add(_tag)
							else:
								r.tags.create(name=field['tags'])
				if status=="inserted":
					init_field = dict(field)
					# 处理group字段
					# 新建不存在的group
					_group = Group.get(name=field['group'])
					if _group:
						init_field['group'] = _group
					else:
						init_field['group'] = Group(name=field['group'])
					# 处理tags字段
					# 新建不存在的tag
					init_field['tags'] = []
					for tag in field['tags'].split(','):
						if tag:
							_tag = Tag.get(name=tag)
							if _tag:
								init_field['tags'].append(_group)
							else:
								init_field['tags'].append(Tag(name=tag))
					# 
					r = Person(**init_field)
					# 提交以更新id
					orm.commit()
					tid[0] = str(r.id)
				if status=="deleted":
					r = Person[gr_id]
					Person[gr_id].delete()
			# 插入一条 action xml item
			act = et.Element("action")
			act.set("type",status)
			act.set("sid",gr_id)
			act.set("tid",tid[0])
			res.append(act)
		self.write_xml(res)


class contacts_group_options_handler(base_handler):
	def get(self):
		xml_data = et.Element("data")
		with orm.db_session:
			for _group in Group.select():
				xml_item = et.Element("item")
				xml_item.set("value",_group.name)
				xml_item.set("label",_group.name)
				xml_data.append(xml_item)
		self.write_xml(xml_data)

if __name__ == "__main__":
	settings = {
		'autoreload': True,
		'static_path': 'static',
		'static_url_prefix': '/static/',
	}
	app = tweb.Application([
		(r"/data/contacts/group/options",contacts_group_options_handler),
		(r"/data/contacts",contacts_handler),
		(r"/", MainHandler),
	],**settings)
	app.listen(8080)
	tioloop.IOLoop.instance().start()