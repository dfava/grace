#!/usr/bin/env python3
# Copyright (C) 2020, Daniel S. Fava. All Rights Reserved.

import sys
from t2g import *
import unittest


class TestStateMachine(unittest.TestCase):

  def test_send(self):
    trans = [("chansend", {'tid' : 1, 'base' : '0x100', 'size' : '0x50'}),
             ("acquire", {'tid' : 1, 'addr' : '0x100'}),
             ("release", {'tid' : 1, 'addr' : '0x100'})]
    (curr, ss) = StateMachine.run("init", None, [trans[0]],debug=False)
    assert(curr == "send")
    (curr, ss) = StateMachine.run(curr, ss, [trans[1]],debug=False)
    assert(curr == "send_acq")
    (curr, ss) = StateMachine.run(curr, ss, [trans[2]],debug=False)
    assert(curr == "init")

  def test_send2(self):
    trans = [("chansend", {'tid' : 1, 'base' : '0x100', 'size' : '0x50'}),
             ("acquire", {'tid' : 1, 'addr' : '0x10'}),
             ("release", {'tid' : 1, 'addr' : '0x100'})]
    (curr, ss) = StateMachine.run("init", None, [trans[0]],debug=False)
    assert(curr == "send")
    try:
      (curr, ss) = StateMachine.run(curr, ss, [trans[1]],debug=False)
    except AssertionError:
      return
    assert(0)

  def test_send3(self):
    trans = [("chansend", {'tid' : 1, 'base' : '0x100', 'size' : '0x50'}),
             ("acquire", {'tid' : 1, 'addr' : '0x100'}),
             ("release", {'tid' : 1, 'addr' : '0x10'})]
    (curr, ss) = StateMachine.run("init", None, [trans[0]],debug=False)
    assert(curr == "send")
    (curr, ss) = StateMachine.run(curr, ss, [trans[1]],debug=False)
    assert(curr == "send_acq")
    try:
      (curr, ss) = StateMachine.run(curr, ss, [trans[2]],debug=False)
    except AssertionError:
      return
    assert(0)

  def test_send4(self):
    trans = [("chansend", {'tid' : 1, 'base' : '0x100', 'size' : '0x50'}),
             ("acquire", {'tid' : 1, 'addr' : '0x100'}),
             ("release", {'tid' : 1, 'addr' : '0x110'})]
    (curr, ss) = StateMachine.run("init", None, [trans[0]],debug=False)
    assert(curr == "send")
    (curr, ss) = StateMachine.run(curr, ss, [trans[1]],debug=False)
    assert(curr == "send_acq")
    try:
      (curr, ss) = StateMachine.run(curr, ss, [trans[2]],debug=False)
    except AssertionError:
      return
    assert(0)


  def test_send5(self):
    trans = [("chansend", {'tid' : 1, 'base' : '0x100', 'size' : '0x50'}),
             ("acquire", {'tid' : 1, 'addr' : '0x160'}),
             ("release", {'tid' : 1, 'addr' : '0x160'})]
    (curr, ss) = StateMachine.run("init", None, [trans[0]],debug=False)
    assert(curr == "send")
    try:
      (curr, ss) = StateMachine.run(curr, ss, [trans[1]],debug=False)
    except AssertionError:
      return
    assert(False)

  def test_send6(self):
    trans = [("chansend", {'tid' : 1, 'base' : '0x100', 'size' : '0x50'}),
             ("closechan", {'tid' : 1, 'addr' : '0x100'})]
    (curr, ss) = StateMachine.run("init", None, [trans[0]],debug=False)
    assert(curr == "send")
    try:
      (curr, ss) = StateMachine.run(curr, ss, [trans[1]],debug=False)
    except KeyError:
      return
    assert(False)

  def test_send7(self):
    trans = [("chansend", {'tid' : 1, 'base' : '0x100', 'size' : '0x50'}),
             ("release_merge", {'tid' : 1, 'addr' : '0x100'})]
    (curr, ss) = StateMachine.run("init", None, [trans[0]],debug=False)
    assert(curr == "send")
    try:
      (curr, ss) = StateMachine.run(curr, ss, [trans[1]],debug=False)
    except KeyError:
      return
    assert(False)


def main(argv):
  unittest.main()   


if __name__ == "__main__":
  sys.exit(main(sys.argv))
