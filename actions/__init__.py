"""
actions — Kumpulan tools Derry (Fase 2B).

  from actions import terminal, files, termux

  terminal.run("ls ~/")          -> {ok, returncode, stdout, ...}
  files.read("catatan.txt")      -> {ok, content, ...}
  files.write("out.txt", "isi")
  termux.notify("Judul", "Isi")
  termux.battery()               -> {ok, data: {...}}
"""
from actions import terminal, files, termux

__all__ = ["terminal", "files", "termux"]
