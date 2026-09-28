// Feed this check a JSON plan from WebAdapter._serialize_plan on stdin.
// Executes the actual browser rendering functions with a minimal DOM fixture.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const plan = JSON.parse(fs.readFileSync(0, 'utf8'));
const script = fs.readFileSync(path.join(__dirname, '../../src/web/static/app.js'), 'utf8');

class Element {
  constructor() {
    this.children = []; this.value = ''; this.textContent = '';
    this.classList = {toggle() {}, add() {}, remove() {}};
  }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener() {}
}
const elements = new Map();
const byId = id => {
  if (!elements.has(id)) elements.set(id, new Element());
  return elements.get(id);
};
const buttons = ['all','included','excluded','blocked'].map(filter => {
  const button = new Element(); button.dataset = {filter};
  button.count = new Element(); button.querySelector = () => button.count;
  return button;
});
byId('decision-filters').querySelectorAll = () => buttons;
const state = {decisionFilter:'included', selectedDecision:null};
const context = vm.createContext({state, byId,
  document:{createElement:() => new Element()},
  text:(id,value) => {byId(id).textContent=String(value);},
  humanBytes:String, renderInspector() {}, activity() {}, refreshActionStates() {},
});
function extract(name, next) {
  return script.slice(script.indexOf(`function ${name}(`),script.indexOf(`function ${next}(`));
}
vm.runInContext(extract('renderPlan','invalidateSourcePlan') + extract('renderDecisions','renderInspector'),context);
context.renderPlan(plan);
assert.equal(byId('count-included').textContent,'1');
assert.equal(byId('count-excluded').textContent,'1');
assert.equal(byId('count-blocked').textContent,'1');
assert.deepEqual(buttons.map(button=>button.count.textContent),[3,1,1,1]);
for (const [filter,label] of [['included','Included'],['excluded','Excluded'],['blocked','Blocked']]) {
  state.decisionFilter=filter;
  context.renderDecisions();
  const rows=byId('decision-rows').children;
  assert.equal(rows.length,1,filter);
  assert.equal(rows[0].children[1].textContent,label);
  assert.equal(rows[0].className,`state-${filter}`);
}
state.decisionFilter='all'; context.renderDecisions();
assert.equal(byId('decision-rows').children.length,3);
byId('decision-search').value='missing'; context.renderDecisions();
assert.equal(byId('decision-rows').children.length,0);
console.log('Service-to-browser rendering passed: counts, Included/Excluded/Blocked/All, colors, and search');
