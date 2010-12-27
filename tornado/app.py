import tornado.httpserver
import tornado.ioloop
import tornado.web
import os.path
import logging
import random
import string
import time

class MainHandler(tornado.web.RequestHandler):
  def get(self):
    self.render('index.html', title='Don\t Asplode!', ship_id=self.generate_id(6))
  def generate_id(self, length):
    return ''.join(random.choice(string.letters + string.digits) for i in xrange(length))


class MessageMixin(object):
  waiters = []
  cache = []
  cache_size = 200

  def wait_for_messages(self, callback, cursor=None):
    cls = MessageMixin
    if cursor:
      index = 0
      for i in xrange(len(cls.cache)):
        index = len(cls.cache) - i - 1
        if cls.cache[index]["id"] == cursor: break
      recent = cls.cache[index + 1:]
      if recent:
        callback(recent)
        return
    cls.waiters.append(callback)

  def new_messages(self, messages):
    cls = MessageMixin
    logging.info("Sending new message to %r listeners", len(cls.waiters))
    for callback in cls.waiters:
      try:
        callback(messages)
      except:
        logging.error("Error in waiter callback", exc_info=True)
    cls.waiters = []
    cls.cache.extend(messages)
    if len(cls.cache) > self.cache_size:
      cls.cache = cls.cache[-self.cache_size:]


class NewMoveHandler(tornado.web.RequestHandler, MessageMixin):
  def post(self):
    ship_id = self.get_argument('ship_id')
    new_x = self.get_argument('new_x')
    new_y = self.get_argument('new_y')
    #logging.error('Movement by ship: '+ self.get_argument('ship_id')  +' to ('+ self.get_argument('new_x') +', '+ self.get_argument('new_y') +')')
    message = {
      "id": ship_id,
      "new_x": new_x,
      "new_y": new_y,
    }
    self.write(message)
    self.new_messages([message])

class GetMoveHandler(tornado.web.RequestHandler, MessageMixin):
  @tornado.web.asynchronous
  def get(self):
    if self._finished:
      return
    self.wait_for_messages(self.async_callback(self.on_new_messages))
    self.finish()

  def post(self):
    if self.request.connection.stream.closed() or self._finished:
      return
    cursor = self.get_argument("cursor", None)
    self.wait_for_messages(
      self.async_callback(self.on_new_messages),
      cursor = cursor
    )
    self.finish()

  def on_new_messages(self, messages):
    # Closed client connection
    if self.request.connection.stream.closed() or self._finished:
      return
    self.finish(dict(messages=messages))

settings = {
  "static_path": os.path.join(os.path.dirname(__file__), "assets"),
}
application = tornado.web.Application([
  (r"/", MainHandler),
  (r"/move", NewMoveHandler), #/([0-9]+)/([0-9]+)", MoveHandler),
  (r"/update", GetMoveHandler),
], **settings)

if __name__ == "__main__":
  http_server = tornado.httpserver.HTTPServer(application)
  http_server.listen(8888)
  tornado.ioloop.IOLoop.instance().start()

