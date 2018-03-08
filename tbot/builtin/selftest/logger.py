"""
TBot logger selftests
---------------------
"""
import tbot

@tbot.testcase
@tbot.cmdline
def selftest_logger(tb: tbot.TBot) -> None:
    """ Test logger """
    text = """\
Esse eligendi optio reiciendis. Praesentium possimus et autem.
Ea in odit sit deleniti est nemo. Distinctio aspernatur facere aut culpa.

Sit veniam ducimus nihil. Totam enim consequuntur vel assumenda quisquam.
Voluptates quidem fugit qui laudantium quia perspiciatis voluptatem
expedita. Placeat et possimus iste explicabo asperiores ipsum.

Magnam commodi libero molestiae. A sequi et qui architecto magni quos.
Rerum consequatur tempora quo nostrum qui. Sint aperiam non quia
consectetur numquam.

Facilis dolorem voluptate laudantium vero quis. Voluptatem quia ipsa
quo pariatur iusto odio omnis. Nulla necessitatibus sapiente et
perferendis dolor. Tempore at ipsum eos molestiae nobis error corporis."""

    custom_ev = tbot.logger.CustomLogEvent(["custom", "event"], text,
                                           tbot.logger.Verbosity.INFO,
                                           {"text": text})

    tb.log.log(custom_ev)