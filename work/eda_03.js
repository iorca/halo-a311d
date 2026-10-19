const r = await eda.sch_Netlist.getNetlist("Protel2");
const out = {};
// 统计 CN3 上所有以 WIFI_ 开头的信号 -> 说明这些是 WiFi SDIO，走核心板哪个 sdio 由核心板决定
const lines = r.split(/\r?\n/);
out.note = "netlist only covers bottom board; sdio node count is a SoC(A311D) property, not in netlist";
return out;