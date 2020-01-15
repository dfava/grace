#!/usr/bin/env python3
# Copyright (C) 2020, Daniel S. Fava. All Rights Reserved.

import os
import sys
from grace import *
import unittest


class TestFresh(unittest.TestCase):
  def test_diff(self):
    fresh = Fresh()
    a = fresh.fresh()
    b = fresh.fresh()
    assert(a!=b)
    

class TestEvent(unittest.TestCase):

  def test_write(self):
    ev = Event.write('m', 'z')
    assert(ev.isWrite() == True)
    assert(ev.isRead() == False)
    assert(ev.getType() == 'w')
    assert(ev.getVar() == 'z')
    assert(ev.getLabel() == 'm')

  def test_read(sefl):
    ev = Event.read('m2', 'x')
    assert(ev.isWrite() == False)
    assert(ev.isRead() == True)
    assert(ev.getType() == 'r')
    assert(ev.getVar() == 'x')
    assert(ev.getLabel() == 'm2')

  def test_eq(self):
    ev1 = Event.write('m', 'z')
    assert(ev1 == Event.write('m', 'z')) # equal although different instances
    assert(ev1 != Event.read('m', 'z'))
    assert(ev1 != Event.write('m2', 'z'))
    assert(ev1 != Event.write('m', 'y'))

  def test_into_set(self):
    s = set()
    ev1 = Event.write('m', 'z')
    ev2 = Event.read('m', 'z')
    ev3 = Event.write('m', 'z')
    s.add(ev1)
    assert(ev1 in s)
    assert(ev3 in s)
    assert(ev2 not in s)


class TestVar(unittest.TestCase):
  def test_create(self):
    fresh = Fresh()
    m = fresh.fresh()
    v = Var('z',m)
    assert(v.m == m)
    assert(v.rds.hb <= set())
    assert(v.rds.hb >= set())

  def test_read(self):
    fresh = Fresh()
    v = Var('z', fresh.fresh())
    v.read(Event.read(fresh.fresh(),'z'), HB())
    assert(len(v.rds.hb) == 1)
    v.read(Event.read(fresh.fresh(),'z'), HB())
    assert(len(v.rds.hb) == 2)
    v.read(Event.read(fresh.fresh(),'z'), HB())
    assert(len(v.rds.hb) == 3)

  def test_write(self):
    fresh = Fresh()
    v = Var('z', fresh.fresh())
    m = fresh.fresh()
    v.write(Event.write(m,'z'))
    assert(v.m == m)
    assert(v.rds.hb <= set())
    assert(v.rds.hb >= set())

  def test_write_2(self):
    fresh = Fresh()
    v = Var('z', fresh.fresh())
    v.read(Event.read(fresh.fresh(),'z'), HB())
    assert(len(v.rds.hb) == 1)
    v.read(Event.read(fresh.fresh(),'z'), HB())
    assert(len(v.rds.hb) == 2)
    v.read(Event.read(fresh.fresh(),'z'), HB())
    assert(len(v.rds.hb) == 3)
    m = fresh.fresh()
    v.write(Event.write(m,'z'))
    assert(v.m == m)
    assert(v.rds.hb <= set())
    assert(v.rds.hb >= set())

  def test_write_fail(self):
    fresh = Fresh()
    v = Var('z', fresh.fresh())
    m = fresh.fresh()
    try:
      v.write(Event.write(m,'x'))
    except:
      return
    assert(False)

  def test_write_fail_2(self):
    fresh = Fresh()
    v = Var('z', fresh.fresh())
    m = fresh.fresh()
    try:
      v.write(Event.read(m,'z'))
    except:
      return
    assert(False)

   
class TestHB(unittest.TestCase):

  def test_init(self):
    assert(HB().hb >= set())
    assert(HB().hb <= set())

  def test_new(self):
    assert(HB.new(HB()).hb >= set())
    assert(HB.new(HB()).hb <= set())

  def test_new2(self):
    a = HB()
    a.add(Event.read('m1','z'))
    a.add(Event.write('m2','z'))
    a.add(Event.write('m3','x'))
    a.add(Event.read('m4','z'))
  
    b = HB.new(a)
    assert(b.hb >= a.hb)
    assert(b.hb <= a.hb)

  def test_new3(self):
    a = HB()
    a.add(Event.read('m1','z'))
    a.add(Event.write('m2','z'))
    a.add(Event.write('m3','x'))
    a.add(Event.read('m4','z'))
  
    b = HB.new(a)
    assert(b.hb >= a.hb)
    assert(b.hb <= a.hb)

    a.hb.remove(Event.write('m2','z'))
    assert(b.hb >= a.hb)
    assert(not b.hb <= a.hb)

  def test_difference(self):
    a = HB()
    a.add(Event.read('m1','z'))
    a.add(Event.write('m2','z'))
    a.add(Event.write('m3','x'))
    a.add(Event.read('m4','z'))

    b = HB()
    b.add(Event.read('m5','x'))
    b.add(Event.read('m6','x'))
    b.add(Event.write('m3','x'))
    b.add(Event.read('m1','z'))

    c = HB()
    c.add(Event.write('m2','z'))
    c.add(Event.read('m4','z'))

    a.difference_update(b)
    assert(a.hb >= c.hb)
    assert(c.hb >= a.hb)

  def test_update(self):
    a = HB()
    a.add(Event.read('m1','z'))
    a.add(Event.write('m2','z'))
    a.add(Event.write('m3','x'))
    a.add(Event.read('m4','z'))

    b = HB()
    b.add(Event.read('m5','x'))
    b.add(Event.read('m6','x'))
    b.add(Event.write('m3','x'))
    b.add(Event.read('m1','z'))

    assert(not a.hb >= b.hb)
    a.update(b)
    assert(a.hb >= b.hb)
   
  def test_contains(self):
    evs = [Event.read('m1','z'), Event.write('m2','z'), Event.write('m3','x'),Event.read('m4','z')]
    a = HB()
    for e in evs[0:-2]:
      a.add(e)
    for e in evs[0:-2]:
      assert(e in a)
    assert(not evs[-1] in a)
    
  def test_proj(self):
    a = HB()
    a.add(Event.read('m1','z'))
    a.add(Event.write('m2','z'))
    a.add(Event.write('m3','x'))
    a.add(Event.read('m4','z'))
    az = a.proj('z')
    ax = a.proj('x')
    empty = az.proj('x')
    cnt = 0
    for e in list(az.hb):
      assert(e.getVar() == 'z')
      cnt += 1
    assert(cnt == 3)
    cnt = 0
    for e in list(ax.hb):
      assert(e.getVar() == 'x')
      cnt += 1
    assert(cnt == 1)
    assert(empty.hb >= set() and empty.hb <= set())


class TestProc(unittest.TestCase):
  # TODO
  pass

class TestChan(unittest.TestCase):

  def test_chan(self):
    c = Chan('name', 10)
    assert(len(c.fq) == 0)
    assert(len(c.bq) == 10)
    hb = c.send('a')
    assert(len(c.fq) == 1)
    assert(len(c.bq) == 9)
    assert(hb.hb >= HB().hb and hb.hb <= HB().hb)
    hb = c.send('b')
    assert(len(c.fq) == 2)
    assert(len(c.bq) == 8)
    assert(hb.hb >= HB().hb and hb.hb <= HB().hb)
    hb = c.send('c')
    assert(len(c.fq) == 3)
    assert(len(c.bq) == 7)
    assert(hb.hb >= HB().hb and hb.hb <= HB().hb)
    hb = c.recv('1')
    assert(len(c.fq) == 2)
    assert(len(c.bq) == 8)
    assert(hb == 'a')
    hb = c.recv('2')
    assert(len(c.fq) == 1)
    assert(len(c.bq) == 9)
    assert(hb == 'b')
    hb = c.send('d')
    assert(len(c.fq) == 2)
    assert(len(c.bq) == 8)

  def test_chan2(self):
    c = Chan('name', 1)
    hb = c.send('a')
    try:
      hb = c.send('b')
    except AssertionError:
      return
    assert(False)


class TestGrace(unittest.TestCase):

  def test_rw(self):
    gr = Grace(verbose=False)
    gr.initProc(0)
    gr.initVar('z')
    gr.go(0,1)
    assert(gr.read(0, 'z') == None)
    assert(gr.write(1, 'z').isRW() == True)

  def test_ww(self):
    gr = Grace(verbose=False)
    gr.initProc(0)
    gr.initVar('z')
    gr.go(0,1)
    assert(gr.write(0, 'z') == None)
    assert(gr.write(1, 'z').isWW() == True)

  def test_wr(self):
    gr = Grace(verbose=False)
    gr.initProc(0)
    gr.initVar('z')
    gr.go(0,1)
    assert(gr.write(0, 'z') == None)
    assert(gr.read(1, 'z').isWR() == True)

  def test_gc(self):
    gr = Grace(verbose=False)
    gr.initProc(0)
    gr.initVar('z')
    gr.go(0,1)
    gr.write(0,'z')
    assert(Event.write(0, 'z') in gr.procs[1].hb)
    gr.gc()
    assert(Event.write(0, 'z') not in gr.procs[1].hb)

  def test_publish_subscribe(self):
    gr = Grace(verbose=False)
    gr.initProc(0)
    gr.initVar('z')
    gr.mkchan('c', 2)
    gr.go(0,1)
    gr.go(0,2)
    assert(gr.write(0, 'z') == None)
    gr.send(0,'c')
    gr.send(0,'c')
    gr.recv(1,'c')
    gr.recv(2,'c')
    assert(gr.read(1,'z') == None)
    assert(gr.read(2,'z') == None)
    gr.send(1,'c')
    gr.send(2,'c')
    gr.recv(0,'c')
    gr.recv(0,'c')
    assert(gr.write(0, 'z') == None)

      

def main(argv):
  unittest.main()

if __name__ == "__main__":
  sys.exit(main(sys.argv))
