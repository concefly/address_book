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
	name   = orm.Required(str)
	people = orm.Set(Person)

class Group(db.Entity):
	id     = orm.PrimaryKey(int, auto=True)
	name   = orm.Required(str)
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
				# group cell
				cell = et.Element("cell")
				cell.text = i.group.name
				row.append(cell)
				# tag cell
				cell = et.Element("cell")
				cell.text = ", ".join(list(i.tags.name))
				row.append(cell)
				# 
				rows.append(row)
		self.write_xml(rows)

if __name__ == "__main__":
	settings = {
		'autoreload': True,
		'static_path': 'static',
		'static_url_prefix': '/static/',
	}
	app = tweb.Application([
		(r"/data/contacts",contacts_handler),
		(r"/", MainHandler),
	],**settings)
	app.listen(8080)
	tioloop.IOLoop.instance().start()