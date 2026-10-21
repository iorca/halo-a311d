# -*- coding: utf-8 -*-
# 补上 USB3.0/PCIe 冷切换：
#   1) deploy-to-build.sh 安装 userpatches/bootscripts/boot-meson64.cmd
#   2) board conf 打开 CONFIG_CMD_GPIO（boot.cmd 里的 gpio set/clear 需要它）
import io, sys

# ---------- 1) deploy-to-build.sh ----------
p = 'scripts/deploy-to-build.sh'
s = io.open(p, encoding='utf-8').read()
anchor = u'echo "\u2713 customize-image.sh  (overlay -> /boot)"\n'
add = u'''echo "\u2713 customize-image.sh  (overlay -> /boot)"

# -----------------------------------------------------------------------------
# 6. 引导脚本覆盖 —— USB3.0 / PCIe 冷切换
#
#    armbian 优先取 $USERPATCHES_PATH/bootscripts/<BOOTSCRIPT 源名>，命中就用它
#    覆盖自己的那份（lib/functions/rootfs/distro-agnostic.sh:190-195）。
#    本板的 BOOTSCRIPT 源名是 **boot-meson64.cmd**，实测日志：
#      "Deploying boot script .../config/bootscripts/boot-meson64.cmd -> /boot/boot.cmd"
#    armbian-bsp-cli 的 postinst 会用 mkimage 把它编成 /boot/boot.scr。
#
#    ⚠ 只改 boot.cmd 不够：还要
#      - board conf 打开 CONFIG_CMD_GPIO（否则没有 gpio 命令）
#      - dt/meson-halo-a311d-pcie.dts 的 fusb340_hog 改成 output-high
#        （内核 gpio-hog 会覆盖 u-boot 设的电平，两边必须一致）
# -----------------------------------------------------------------------------
BOOT_SRC="$REPO_ROOT/boot/boot-meson64.cmd"
mkdir -p "$UP/bootscripts"
if [ ! -f "$BOOT_SRC" ]; then
    echo "\u2717 缺少 $BOOT_SRC —— 冷切换不会生效" >&2
    exit 1
fi
install -m 0644 "$BOOT_SRC" "$UP/bootscripts/boot-meson64.cmd"
if [ ! -s "$UP/bootscripts/boot-meson64.cmd" ]; then
    echo "\u2717 boot-meson64.cmd 未部署到 $UP/bootscripts" >&2
    exit 1
fi
echo "\u2713 bootscripts/boot-meson64.cmd  (覆盖 armbian boot.cmd，含冷切换)"
'''
assert anchor in s, 'deploy anchor'
s = s.replace(anchor, add, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print(u'✓ patched ' + p)

# ---------- 2) board conf ----------
q = 'config/boards/halo-a311d.conf'
t = io.open(q, encoding='utf-8').read()
old = u'''\trun_host_command_logged scripts/config --enable CONFIG_LED'''
new = u'''\trun_host_command_logged scripts/config --enable CONFIG_LED
\tdisplay_alert "u-boot for ${BOARD}" "enable gpio command for FUSB340 SEL" "info"
\t# ⚠ 必需：boot.cmd 里用 `gpio set/clear GPIOA_2` 驱动 FUSB340 SEL。
\t#   没有 CONFIG_CMD_GPIO 就压根没有 gpio 命令 → 电平切不动 → PCIe 模式起不来。
\t#   （注意不是 CONFIG_CMD_GPIO_READ：SEL 是 SoC 驱动的输出，没有可读的 strap）
\trun_host_command_logged scripts/config --enable CONFIG_CMD_GPIO'''
assert t.count(old) == 1, 'board conf anchor'
t = t.replace(old, new, 1)
io.open(q, 'w', encoding='utf-8', newline='\n').write(t)
print(u'✓ patched ' + q)
