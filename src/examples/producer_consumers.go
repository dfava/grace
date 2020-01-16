package main

var z = 0;
var c = make(chan bool, 2);
var d = make(chan bool, 2);

func t1(end chan bool) (local int) {
  <- c
  local = z // Read from z
  d <- true

  end <- true
  return;
}


func t2(end chan bool) (local int) {
  <- c
  local = z // Read from z
  d <- true

  end <- true
  return;
}

func main() {
  end := make (chan bool, 2)
  go t1(end)
  go t2(end)
  z = 42
  c <- true; c <- true
  <- d; <- d
  z = 43
  <- end; <- end
}
