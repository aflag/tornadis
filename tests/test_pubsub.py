#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.testing
import tornado.ioloop
import tornado.gen

from tornadis.pubsub import PubSubClient
from tornadis.client import Client
from tornadis.exceptions import ClientError
from support import test_redis_or_raise_skiptest


class PubSubClientTestCase(tornado.testing.AsyncTestCase):

    def setUp(self):
        test_redis_or_raise_skiptest()
        super(PubSubClientTestCase, self).setUp()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @tornado.gen.coroutine
    def publish(self, c2):
        yield tornado.gen.sleep(1)
        yield c2.call("PUBLISH", "null", "value0")
        yield c2.call("PUBLISH", "foo1", "value1")
        yield c2.call("PUBLISH", "foo2", "value2")
        yield c2.call("PUBLISH", "bar111", "value3")
        yield c2.call("PUBLISH", "bar222", "value4")

    @tornado.testing.gen_test
    def test_pubsub(self):
        c = PubSubClient()
        c2 = Client()
        yield c.connect()
        yield c2.connect()
        try:
            yield c.pubsub_pop_message()
            raise Exception("exception not raised")
        except:
            pass
        res = yield c.pubsub_subscribe("foo1", "foo2")
        self.assertTrue(res)
        self.assertTrue(c.subscribed)
        self.assertFalse(c2.subscribed)
        try:
            yield c.call("PING")
            raise Exception("exception not raised")
        except:
            pass
        res = yield c.pubsub_psubscribe("bar1*", "bar2*")
        self.assertTrue(res)
        tornado.ioloop.IOLoop.instance().add_future(self.publish(c2), None)
        msg = yield c.pubsub_pop_message()
        self.assertEquals(msg[2], b"value1")
        msg = yield c.pubsub_pop_message()
        self.assertEquals(msg[2], b"value2")
        msg = yield c.pubsub_pop_message()
        self.assertEquals(msg[3], b"value3")
        msg = yield c.pubsub_pop_message()
        self.assertEquals(msg[3], b"value4")
        msg = yield c.pubsub_pop_message(deadline=1)
        self.assertEquals(msg, None)
        yield c.pubsub_unsubscribe("foo1")
        yield c2.call("PUBLISH", "foo1", "value1")
        c2.disconnect()
        msg = yield c.pubsub_pop_message(deadline=1)
        self.assertEquals(msg, None)
        yield c.pubsub_unsubscribe("foo2")
        yield c.pubsub_unsubscribe("foobar")
        yield c.pubsub_punsubscribe("foobar*")
        yield c.pubsub_punsubscribe("bar1*")
        yield c.pubsub_punsubscribe("bar2*")
        self.assertFalse(c.subscribed)
        c.disconnect()

    @tornado.testing.gen_test
    def test_issue17(self):
        c = PubSubClient()
        yield c.connect()
        res = yield c.pubsub_subscribe("foo")
        self.assertTrue(res)
        self.assertTrue(c.subscribed)
        res = yield c.pubsub_unsubscribe()
        self.assertTrue(res)
        self.assertFalse(c.subscribed)
        c.disconnect()

    @tornado.testing.gen_test
    def test_empty_subscribe(self):
        c = PubSubClient()
        yield c.connect()
        try:
            yield c.pubsub_subscribe()
            raise Exception("ClientError not raised")
        except ClientError:
            pass
        c.disconnect()
