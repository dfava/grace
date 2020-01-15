# Copyright (C), 2020 Daniel S. Fava. All Rights Reserved.

import os
import sys
import inspect


tool_name = os.path.splitext(os.path.basename(__file__))[0]

class Fresh():
  def __init__(self):
    self.cnt = 0

  def fresh(self):
    ret = self.cnt
    self.cnt += 1
    return ret


class Event():
  def __init__(this, evtype, m, var):
    assert(evtype in ['r', 'w'])
    this.ev = (evtype,m,var)

  @classmethod
  def read(cls,m,var):
    return Event('r',m,var)

  @classmethod
  def write(cls,m,var):
    return Event('w',m,var)

  def isRead(this):
    t,m,v = this.ev
    return t == 'r'

  def isWrite(this):
    t,m,v = this.ev
    return t == 'w'

  def getVar(this):
    t,m,v = this.ev
    return v

  def getType(this):
    t,m,v = this.ev
    return t

  def getLabel(this):
    t,m,v = this.ev
    return m

  def __hash__(this):
    return hash(this.ev)

  def __eq__(self, rhs):
    return isinstance(rhs, Event) and self.ev == rhs.ev

  def __str__(this):
    return str(this.ev)

  def __repr__(this):
    return str(this.ev)


class Var():
  def __init__(this, var, m):
    this.var = var
    this.m = m
    assert(type(m) == int)
    this.rds = HB()

  def write(this, w):
    assert(w.getVar() == this.var)
    assert(w.getType() == 'w')
    this.m = w.getLabel()
    this.rds = HB()

  def read(this, r, sub):
    assert(r.getVar() == this.var)
    assert(r.getType() == 'r')
    this.rds.difference_update(sub)
    this.rds.add(r)

  def __str__(this):
    return "%s, %s, %s" % (this.var, this.m, this.rds)


class HB():
  def __init__(this):
    this.hb = set()

  @classmethod
  def new(cls, other):
    ret = HB()
    ret.hb = set(other.hb)
    return ret

  def update(this, other):
    this.hb.update(other.hb)
    
  def add(this,ev):
    this.hb.add(ev)

  def difference_update(this,t):
    for e in list(t.hb):
      this.hb.discard(e)

  def __contains__(this,ev):
    return ev in this.hb

  def proj(this,var):
    ret = HB()
    ret.hb = set([e for e in list(this.hb) if e.getVar() == var])
    return ret

  def __str__(this):
    return "HB(%s)" % list(this.hb)

  def issuperset(this,t):
    return this.hb.issuperset(t.hb)

  def __iter__(this):
    return this.hb.__iter__()

  def remove(this,ev):
    this.hb.remove(ev)


class Proc():
  def __init__(this, pid):
    this.id = pid
    this.hb = HB()

  def write(this, w, rds, wp, sub):
    assert(w in this.hb)
    assert(this.hb.issuperset(rds))
    this.hb.difference_update(sub)
    this.hb.add(wp)
    assert(w not in this.hb)

  def read(this, w, r, sub):
    assert(w in this.hb)
    this.hb.difference_update(sub)
    this.hb.add(r)
    this.hb.add(w)

  def __str__(this):
    return "proc[%s]: %s" % (this.id, this.hb)


class Chan():
  def __init__(this, cid, size):
    assert(size >= 0)
    this.id = cid
    this.size = size
    this.fq = []
    this.bq = [HB() for i in range(0,size)] # bottom elements

  def send(this, hb):
    assert(len(this.fq) < this.size)
    this.fq.insert(0,hb)
    ret = this.bq.pop()
    assert(len(this.fq)+len(this.bq)==this.size)
    return ret

  def recv(this, hb):
    assert(len(this.fq) > 0)
    this.bq.insert(0,hb)
    ret = this.fq.pop()
    assert(len(this.fq)+len(this.bq)==this.size)
    return ret

  def __str__(this):
    fq = ["%s" % i for i in this.fq]
    bq = ["%s" % i for i in this.bq]
    return "%s, %s, %s, %s" % (this.id, this.size, fq, bq)


class DataRace():
  def __init__(self, drType, message):
    assert(drType in ['rw', 'ww', 'wr'])
    self.drType = drType
    self.message = message

  def isRW(self):
    assert(self.drType in ['rw', 'ww', 'wr'])
    return self.drType == 'rw'

  def isWW(self):
    assert(self.drType in ['rw', 'ww', 'wr'])
    return self.drType == 'ww'

  def isWR(self):
    assert(self.drType in ['rw', 'ww', 'wr'])
    return self.drType == 'wr'


class Grace():
  def __init__(self, verbose=True):
    self.fsh = Fresh()

    self.verbose = verbose
    # var -> (m,{m'})
    self.vs = {}

    # pid -> {(m,z)}
    self.procs = {}

    # cid -> Chan
    self.chans = {}

  def fresh(self):
    return self.fsh.fresh()

  def printProcs(self, fmt=None):
    if fmt == None:
      for pid in self.procs.keys():
        print(self.procs[pid])
    elif fmt == "tikz":
      for pid in self.procs.keys():
        print(pid)
      print("Here")
    elif fmt == "dot":
      print("graph {")
      print("  rankdir=LR;")
      print("  ranksep = 4;")
      edges = {}
      for pid in self.procs.keys():
        for ev in self.procs[pid].hb:
          v = Event.var(ev)
          t = Event.evtype(ev)
          try:
            edges['%s -- "%s"' % (pid, v)] += 1
          except KeyError:
            edges['%s -- "%s"' % (pid, v)] = 1
      for edge in edges:
        print("  %s" % edge)
      print("}")
    else:
      assert(0)

  def printVars(self):
    for v in self.vs.keys():
      print(self.vs[v])
  
  def printChans(self):
    for c in self.chans.keys():
      print(self.chans[c])
  
  def printReport(self, print_procs=True,print_vars=True,print_chans=True, fmt=None):
    if print_procs:
      self.printProcs(fmt=fmt)
      print()
    if print_vars:
      self.printVars()
      print()
    if print_chans:
      self.printChans()
  
  
  def initVar(self, var):
    assert(var not in self.vs.keys())
    m = self.fresh()
    self.vs[var] = Var(var,m)    # Create a new var with a unique initial write label
    w = Event.write(m,var)
    # Must put the initialization of var in all processes' hb
    for pid in self.procs:
      self.procs[pid].hb.add(w)
  
  
  def initProc(self, pid, hb=None):
    assert(pid not in self.procs.keys())
    self.procs[pid] = Proc(pid)
    if hb != None:
      self.procs[pid].hb = HB.new(hb)
  
  
  def mkchan(self, cid, size):
    assert(cid not in self.chans.keys())
    self.chans[cid] = Chan(cid, size)
  
  
  def gc(self, pid=None, verbose=False):
    '''Rule R-GC'''
    if self.verbose and verbose:
      print("%s: %s %s" % (tool_name, inspect.currentframe().f_code.co_name, "" if pid == None else pid))
  
    assert(pid == None or pid in self.procs.keys())
    pids = [pid] if pid != None else self.procs.keys()
    for pid in pids:
      for event in list(self.procs[pid].hb):
        #print(event)
        v = event.getVar()
        m = event.getLabel()
        assert(v in self.vs)
        #print(self.vs[v].m)
        if Event.isRead(event):
          if event not in self.vs[v].rds:
            if verbose:
              print("Removing ",  event, " from proc ", pid)
            self.procs[pid].hb.remove(event)
        elif Event.isWrite(event):
          if m != self.vs[v].m:
            if verbose:
              print("Removing ", event, " from proc ", pid)
            self.procs[pid].hb.remove(event)
        else:
          assert(False)
  
  
  def go(self, ppid, cpid):
    '''Rule R-Go'''
    if self.verbose:
      print("%s: %s %s %s" % (tool_name, inspect.currentframe().f_code.co_name, ppid, cpid))
  
    assert(ppid in self.procs.keys())
    assert(cpid not in self.procs.keys())
    self.initProc(cpid, self.procs[ppid].hb)
  
  
  def write(self, pid, var):
    '''Rule R-Write'''
    if self.verbose:
      print("%s: %s %s %s" % (tool_name, inspect.currentframe().f_code.co_name, pid, var))
  
    assert(pid in self.procs.keys())
    if var not in self.vs.keys():  # In case var is not yet in vars
      self.initVar(var)
  
    # Check for write-write race
    w = Event.write(self.vs[var].m,var)
    if w not in self.procs[pid].hb:
      message = "%s: (ERR) Data race, write-write %s %s\n" % (tool_name, pid, var)
      message += "  %s\n" % w
      message += "  %s\n" % self.procs[pid]
      message += "  %s" % self.vs[var]
      if self.verbose:
        print(message)
      return DataRace('ww', message)
  
    # Check for read-write race
    if not self.procs[pid].hb.issuperset(self.vs[var].rds):
      message = "%s: (ERR) Data race, read-write %s %s\n" % (tool_name, pid, var)
      message += "  %s\n" % self.procs[pid]
      message += "  %s" % self.vs[var]
      if self.verbose:
        print(message)
      return DataRace('rw', message)
  
    event = Event.write(self.fresh(),var)
    self.vs[var].write(event) # Update memory
    proj = self.procs[pid].hb.proj(var)  # To be subtracted from HB
    self.procs[pid].write(w, self.vs[var].rds, event, proj) # Update proc
  
  
  def read(self, pid, var):
    '''Rule R-Read'''
    if self.verbose:
      print("%s: %s %s %s" % (tool_name, inspect.currentframe().f_code.co_name, pid, var))
  
    assert(pid in self.procs.keys())
    if var not in self.vs.keys():  # In case var is not yet in vars
      self.initVar(var)
  
    w = Event.write(self.vs[var].m,var)
    if w not in self.procs[pid].hb:
      message = "%s: (ERR) Data race, write-read %s %s\n" % (tool_name, pid, var)
      message += "  %s\n" % w
      message += "  %s\n" % self.procs[pid]
      message += "  %s" % self.vs[var]
      if self.verbose:
        print(message)
      return DataRace('wr', message)
    
    # Create a read event, update var (ie. memory) and proc
    event = Event.read(self.fresh(),var)
    proj = self.procs[pid].hb.proj(var)  # To be subtracted from HBs
    self.vs[var].read(event, proj) # Update memory
    self.procs[pid].read(w, event, proj) # Update proc
  
  
  def send(self, pid, chan):
    '''Rule R-Send'''
    if self.verbose:
      print("%s: %s %s %s" % (tool_name, inspect.currentframe().f_code.co_name, pid, chan))
  
    #assert(chan in self.chans.keys())
    if chan not in self.chans.keys():
      self.mkchan(chan, 1)
    assert(pid in self.procs.keys())
    hb   = HB.new(self.procs[pid].hb)
    hbpp = self.chans[chan].send(hb)
    self.procs[pid].hb.update(hbpp)
    self.gc(pid)
    assert(self.procs[pid].hb != None)
  
  
  def recv(self, pid, chan):
    '''Rule R-Rec'''
    if self.verbose:
      print("%s: %s %s %s" % (tool_name, inspect.currentframe().f_code.co_name, pid, chan))
  
    assert(chan in self.chans.keys())
    assert(pid in self.procs.keys())
    hb   = HB.new(self.procs[pid].hb)
    hbpp = self.chans[chan].recv(hb)
    self.procs[pid].hb.update(hbpp)
    self.gc(pid)
    assert(self.procs[pid].hb != None)
  
  
  def close(self, pid, chan):
    if self.verbose:
      print("%s: %s %s %s" % (tool_name, inspect.currentframe().f_code.co_name, pid, chan))
    # TODO assert(0)
