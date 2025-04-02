import logging
from datetime import datetime, timezone

logger = logging.getLogger('telegramtastic.common')

# https://www.reddit.com/r/mildlyinteresting/comments/593ao8/telegram_from_greatgrandmother_on_my_birth/
def printThis(to, frm, text, printer):
    now = datetime.now().astimezone().strftime("%d %B %Y %H:%M %Z")
    printer.set_with_default()
    printer.set(double_height=True, double_width=True,bold=True,align="center")
    printer.text("MESHTASTIC TELEGRAM\n")
    printer.text("=" * 21 + "\n\n")
    printer.set_with_default()
    body = f"Recieved: {now}\n\n{text}\n\n".upper()
    printer.text(body)
    printer.set(align="center")
    out = f"--{frm.short_name} / {frm.long_name}\n\n".upper()
    printer.text(out)
    printer.set_with_default()
    printer.cut()