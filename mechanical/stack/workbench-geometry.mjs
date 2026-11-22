// Deliberately no CAD dimensions here. The interactive study is the geometry authority.
import { stackModel } from '../../workbench/stack.js';

function objectArg(value, name) {
  const obj = JSON.parse(value ?? '{}');
  if (obj === null || typeof obj !== 'object' || Array.isArray(obj))
    throw new Error(`${name} must be a JSON object`);
  return obj;
}

const options = objectArg(process.argv[2], 'stack options');
const layoutState = objectArg(process.argv[3], 'layout state');
const model = stackModel(options, layoutState);
if (!Array.isArray(model.solids) || !model.solids.length)
  throw new Error('stackModel returned no solids');
process.stdout.write(
  JSON.stringify({
    schema: 1,
    units: 'mm',
    source: 'workbench/stack.js : stackModel',
    options: model.options,
    layoutState,
    solids: model.solids,
  }),
);
