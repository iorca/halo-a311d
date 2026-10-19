"""分析 GitHub Actions 日志的时间分布，找出耗时集中区。

用法: python analyze.py <logfile>

注意: gh --log 输出的行首含 BOM（\\xef\\xbb\\xbf），
必须用二进制读取—— utf-8-sig 只剥文件开头的 BOM，剥不掉行内的。
"""
import re
import sys
from collections import Counter
from datetime import datetime

TS = re.compile(rb'(2026-\d\d-\d\dT\d\d:\d\d:\d\d)')

# armbian / make 用这些特征标记阶段
MARKS = [
    ('拉源码(clone)', rb'Getting sources from|Fetching updates from'),
    ('checkout 源码', rb'HEAD is now at|Checking out to clean sources'),
    ('配置 defconfig', rb'olddefconfig'),
    ('编译 .c -> .o', rb'\tCC      |\tHOSTCC |\tAS      '),
    ('链接', rb'\tLD      |Objcopy '),
    ('dtb 编译', rb'dtb|\.dtb\.bin'),
    ('打包 deb', rb'dpkg-deb|building deb'),
    ('rootfs 构建', rb'debootstrap|debootstrap'),
    ('镜像打包', rb'Creating image|Building image|\.img'),
]


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else 'klog.tmp'
    data = open(path, 'rb').read()

    events = [(m.start(), m.group(1).decode()) for m in TS.finditer(data)]
    if not events:
        print('日志里没有时间戳')
        return

    t0 = datetime.fromisoformat(events[0][1] + '+00:00')
    times = [datetime.fromisoformat(t + '+00:00') for _, t in events]
    span = int((max(times) - t0).total_seconds() // 60)

    print('=== 每分钟日志行数（活跃度）===')
    per_min = Counter(int((t - t0).total_seconds() // 60) for t in times)
    for m in range(span + 1):
        c = per_min.get(m, 0)
        if c:
            print('  +%2dmin %-42s %d' % (m, '#' * max(1, c // 60), c))

    print('\n=== 关键阶段首次出现（累计分钟）===')
    for label, pat in MARKS:
        rx = re.compile(pat)
        for off, ts in events:
            if rx.search(data[off:off + 8192]):
                t = datetime.fromisoformat(ts + '+00:00')
                print('  +%3dmin  %s' % ((t - t0).total_seconds() // 60, label))
                break

    print('\n总跨度 %d min, 日志行 %d' % (span, len(times)))


if __name__ == '__main__':
    main()
