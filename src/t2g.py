#!/usr/bin/env python3
# Copyright (C) 2020, Daniel S. Fava. All Rights Reserved.

import os
import re
import sys
import traceback
import grace

DEBUG = True
VERBOSE = False

TSAN_INVALID_TID = '8129'

dbgCtx = {}

class StateMachine:

  # Does not change
  sm = {    # State machine
    # (state, input) : [next state, lambda symbolic_state, symbolic_input : next_symbolic_state]
    ("init", "")              : ["init", lambda ss, sinp : None],
    ("init", "chansend")      : ["send", lambda ss, sinp : sinp],
    ("send", "acquire")       : ["send_acq", lambda ss, sinp : 
      (_ for _ in ()).throw(AssertionError("%s != %s" % (ss,sinp))) if ss['tid']!=sinp['tid'] 
      else 
      (_ for _ in ()).throw(AssertionError("addr less than base: %s %s" % (ss,sinp))) if int(sinp['addr'],16)<int(ss['base'],16)
      else
      (_ for _ in ()).throw(AssertionError("addr less than base: %s %s" % (ss,sinp))) if int(sinp['addr'],16)>(int(ss['base'],16)+int(ss['size'],16))
      else sinp],
    ("send_acq", "release")   : ["init", lambda ss, sinp :
      (_ for _ in ()).throw(AssertionError("%s != %s" % (ss,sinp))) if ss['tid']!=sinp['tid'] 
      else 
      (_ for _ in ()).throw(AssertionError("%s != %s" % (ss,sinp))) if ss['addr']!=sinp['addr']
      else None],
    ("init", "acquire")       : ["recv", lambda ss, sinp : sinp],
    ("recv", "release")       : ["init", lambda ss, sinp :
      (_ for _ in ()).throw(AssertionError("%s != %s" % (ss,sinp))) if ss['tid']!=sinp['tid'] 
      else 
      (_ for _ in ()).throw(AssertionError("%s != %s" % (ss,sinp))) if ss['addr']!=sinp['addr']
      else None],
    ("init", "release_merge") : ["merge", lambda ss, sinp : sinp],
    ("merge", "acquire")      : ["init", lambda ss, sinp :
      (_ for _ in ()).throw(AssertionError("%s != %s" % (ss,sinp))) if ss['tid']!=sinp['tid'] 
      else 
      (_ for _ in ()).throw(AssertionError("%s != %s" % (ss,sinp))) if ss['addr']!=sinp['addr']
      else None],
    ("init", "closechan")     : ["close", lambda ss, sinp : sinp],
    ("close", "release")      : ["init", lambda ss, sinp :
      (_ for _ in ()).throw(AssertionError("%s != %s" % (ss,sinp))) if ss['tid']!=sinp['tid'] 
      else 
      (_ for _ in ()).throw(AssertionError("%s != %s" % (ss,sinp))) if ss['addr']!=sinp['addr']
      else None],
  }

  @classmethod
  def check_invariants(cls, initial):
    states = set()
    transitions = set()
    for (s,t) in cls.sm.keys():
      states.add(s)
      transitions.add(t)
    assert(states.intersection(transitions)==set())
    assert(initial in states)
    return (states, transitions)

  @classmethod
  def run(cls, initial, ss, inputs, debug=DEBUG):
    '''Run the state machine'''
    cls.check_invariants(initial)
    curr = initial
    for (inp,sinp) in inputs:
      next_state = cls.sm[(curr, inp)][0]
      try: 
        ss = cls.sm[(curr, inp)][1](ss, sinp)
      except AssertionError as e:
        if debug:
          traceback.print_exc()
          print(dbgCtx)
          sys.exit(1)
        else:
          raise e
      curr = next_state
    return (curr, ss)




def parse(fhandle):
  potential_chans = {}

  gr = grace.Grace()
  gr.initProc('0')

  # State machine
  curr = {} #"init"
  ss = {} #= None

  # Stack
  stack = {}

  s_go = re.compile('__tsan_go_start,.*,tid=(.*),.*,tid=(.*),.*')
  s_go_end = re.compile('__tsan_go_end,.*,tid=(.*)')
  s_read = re.compile('__tsan_read,.*,tid=(.*),(.*),.*')
  s_write = re.compile('__tsan_write,.*,tid=(.*),(.*),.*')
  s_acquire = re.compile('__tsan_acquire,.*,tid=(.*),(.*)')
  s_release = re.compile('__tsan_release,.*,tid=(.*),(.*)')
  s_release_merge = re.compile('__tsan_release_merge,.*,tid=(.*),(.*)')
  s_chansend = re.compile('__tsan_read_pc,.*,tid=(.*),(.*),.*,.*,chansend')
  s_closechan = re.compile('__tsan_write_pc,.*,tid=(.*),(.*),.*,.*,closechan')
  s_malloc = re.compile('__tsan_malloc,.*,tid=.*,.*,(.*),(.*)')
  s_func_enter = re.compile('__tsan_func_enter,.*,tid=(.*),.*,(.*)')
  s_func_exit = re.compile('__tsan_func_exit,.*,tid=(.*)')
  idx = 0
  for line in fhandle:
    idx += 1
    dbgCtx['idx'] = idx
    dbgCtx['line'] = line
    if DEBUG and VERBOSE:
      print(line.strip())
      print(curr)
      print(ss)
      print()
    r = s_func_exit.match(line)
    if r:
      tid = r.group(1)
      func = stack[tid].pop()
      print("func_exit ", func, tid)
      continue
    r = s_func_enter.match(line)
    if r:
      tid = r.group(1)
      func = r.group(2)
      if tid not in stack.keys():
        stack[tid] = []
      stack[tid].append(func)
      print("func_enter ", func, tid)
      continue

    # Filter out trace from within sync
    if line.startswith('__tsan_'):
      assert(line.split(',')[2][:4] == 'tid=')
      tid = line.split(',')[2][4:]
      if tid in stack.keys() and stack[tid] != []:
        top_of_stack = stack[tid][-1]
        if top_of_stack.startswith('sync') or \
           top_of_stack.startswith('syscall') or \
           top_of_stack.startswith('fmt'):
          #print("Skipping sync, tid=%s" % tid)
          continue

    r = s_malloc.match(line)
    if r:
      potential_chans["0x%x" % (int(r.group(1),16))] = "0x%x" % (int(r.group(2), 16))
      continue
    r = s_go.match(line)
    if r:
      gr.go(r.group(1),r.group(2))
      continue
    r = s_read.match(line)
    if r:
      gr.read(r.group(1),"0x%x" % (int(r.group(2),16)))
      continue
    r = s_write.match(line)
    if r:
      gr.write(r.group(1),"0x%x" % (int(r.group(2),16)))
      continue
    r = s_closechan.match(line)
    if r:
      tid = r.group(1)
      addr = "0x%x" % (int(r.group(2),16))
      if tid not in curr.keys():
        curr[tid] = "init"
        ss[tid] = None
      (curr[tid], ss[tid]) = StateMachine.run(curr[tid], ss[tid], [("closechan", {'tid': tid, 'addr': addr})])
      continue
    r = s_chansend.match(line)
    if r:
      tid = r.group(1)
      addr = "0x%x" % (int(r.group(2),16))
      # Sometimes we need to take an offset into account, sometimes we don't need to.
      # It depends on `race.go` and how `c.buf` is set in `makechan().`
      base = addr if addr in potential_chans else "0x%x" % (int(addr, 16) - 0x10)
      try:
        assert(base in potential_chans)
      except AssertionError as e:
        if DEBUG:
          print('addr %s' % addr)
          print('base %s' % base)
          print('potential_chans ', potential_chans)
          base = "0x%x" % (int(addr, 16) - 0x10)
          print(base in potential_chans)
        raise e

      size = potential_chans[base]
      if tid not in curr.keys():
        curr[tid] = "init"
        ss[tid] = None
      (curr[tid], ss[tid]) = StateMachine.run(curr[tid], ss[tid], [("chansend", {'tid': tid, 'base': base, 'size': size})])
      continue
    r = s_acquire.match(line)
    if r:
      tid = r.group(1)
      addr = "0x%x" % (int(r.group(2),16))
      if tid not in curr.keys():
        curr[tid] = "init"
        ss[tid] = None
      (curr[tid], ss[tid]) = StateMachine.run(curr[tid], ss[tid], [("acquire", {'tid': tid, 'addr': addr})])
      continue
    r = s_release.match(line)
    if r:
      tid = r.group(1)
      addr = "0x%x" % (int(r.group(2),16))
      tmp = curr[tid]
      (curr[tid], ss[tid]) = StateMachine.run(curr[tid], ss[tid], [("release", {'tid': tid, 'addr': addr})])
      if tmp == "send_acq":
        gr.send(tid, addr)
      elif tmp == "recv":
        dbgCtx['addr'] = addr
        dbgCtx['grace.chans.keys()'] = gr.chans.keys()
        dbgCtx['tid'] = tid
        dbgCtx['stack[%s]' % tid] = stack[tid] if tid in stack.keys() else None
        gr.recv(tid, addr)
      elif tmp == "close":
        gr.close(tid, addr)
      else:
        assert(0)
      del(tmp)
      continue
    r = s_release_merge.match(line)
    if r:
      tid = r.group(1)
      addr = "0x%x" % (int(r.group(2),16))
      if tid not in curr.keys():
        curr[tid] = "init"
        ss[tid] = None
      (curr[tid], ss[tid]) = StateMachine.run(curr[tid], ss, [("release_merge", {'tid': tid, 'addr': addr})])
      continue
    r = s_go_end.match(line)
    if r:
      tid = r.group(1)
      # What does it mean, from the point of view of grace.py (and from the paper)
      # for a thread-id to be reused?
      # Perhaps its best to give it a fake new name?
      print('WARNING: go_end %s' % tid)
      # I'm letting execution continue since, if a new goroutine is created with
      # the same name as the one that ended, grace will assert and error out.
      #assert(0)

  print()
  gr.printReport(print_chans=False)
  gr.gc(verbose=True)
  print()
  gr.printReport(print_chans=False, print_vars=False)
  print()
  #gr.gc(verbose=False)
  #gr.printReport(print_chans=False, print_vars=False, fmt="dot")



def main(argv):
  if len(argv) != 2:
    print("%s %s" % (os.path.basename(__file__), "<TRACE>"))
    sys.exit(1)

  fhandle = open(argv[1], 'r')
  try:
    parse(fhandle)
  except (AssertionError, KeyError) as e:
    traceback.print_exc()
    print(dbgCtx)
    sys.exit(1)



if __name__ == "__main__":
  sys.exit(main(sys.argv))
