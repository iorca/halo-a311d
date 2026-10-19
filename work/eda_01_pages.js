const proj = await eda.dmt_Project.getCurrentProjectInfo();
const pages = await eda.dmt_Schematic.getAllSchematicPagesInfo();
const docs = await eda.dmt_Schematic.getAllSchematicsInfo();
return {
  project: proj ? { name: proj.friendlyName || proj.name, uuid: proj.uuid } : null,
  schematicDocs: (docs || []).map(d => ({ uuid: d.uuid, name: d.name })),
  pages: (pages || []).map(p => ({ uuid: p.uuid, name: p.name, parent: p.parentSchematicUuid }))
};
