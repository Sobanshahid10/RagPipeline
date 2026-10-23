import {test} from 'node:test';
import assert from 'node:assert/strict';
import {safeUrl} from '../lib/safe-url.ts';
import {chatHistoryKey} from '../lib/api.ts';
test('model links cannot execute scripts or disguise protocols',()=>{
  for (const url of ['javascript:alert(1)','data:text/html,payload','vbscript:run','//external.test','/\\external.test','java\nscript:alert(1)']) assert.equal(safeUrl(url),'#');
  assert.equal(safeUrl('https://example.com/source'),'https://example.com/source');
  assert.equal(safeUrl('/documents/123'),'/documents/123');
});
test('conversation history is isolated by verified tenant and account',()=>{
  assert.equal(chatHistoryKey(null),null);
  const first=chatHistoryKey({id:'alice',tenant_id:'tenant-a',email:'alice@example.com'});
  assert.notEqual(first,chatHistoryKey({id:'bob',tenant_id:'tenant-a',email:'bob@example.com'}));
  assert.notEqual(first,chatHistoryKey({id:'alice',tenant_id:'tenant-b',email:'alice@example.com'}));
});
