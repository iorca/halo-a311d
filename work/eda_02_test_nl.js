const ok = await eda.dmt_EditorControl.openDocument("c43aae5469ff4dcc93e21d77c1a3dbdd");
const nl = await eda.sch_netlist.getNetlist("Protel2");
return {
  opened: ok,
  len: nl ? nl.length : 0,
  hasU92: nl ? nl.includes("U92") : false,
  hasU406: nl ? nl.includes("U406") : false,
  hasU84: nl ? nl.includes("U84") : false,
  hasU4012: nl ? nl.includes("U4012") : false,
  hasCN230: nl ? nl.includes("CN230") : false,
  sample: nl ? nl.slice(0, 400) : ""
};
