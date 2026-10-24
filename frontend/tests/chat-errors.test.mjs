import {test} from 'node:test';
import assert from 'node:assert/strict';
import {isSavedChatMessage} from '../lib/chat-history.ts';
import {streamQuery} from '../lib/api.ts';

test('saved and exported answers omit failed requests and placeholders', () => {
  for (const content of ['', 'Answer could not be completed and verified. Please retry or choose another configured model.', '⚠️ Failed to query public knowledge book: unavailable']) {
    assert.equal(isSavedChatMessage({role:'assistant',content}),false);
  }
  assert.equal(isSavedChatMessage({role:'assistant',content:'A cited answer.'}),true);
  assert.equal(isSavedChatMessage({role:'user',content:'My question'}),true);
});

test('an interrupted stream fails instead of appearing complete', async () => {
  const original=globalThis.fetch;
  try {
    globalThis.fetch=async()=>new Response('data: {"type":"token","content":"A"}\n\n');
    const events=[];
    for await(const event of streamQuery('question','test-token')) events.push(event);
    assert.equal(events.at(-1).type,'error');
    assert.match(events.at(-1).message,/before the answer completed/);
  } finally {globalThis.fetch=original;}
});

test('terminal errors stop the stream and retain the failure reason', async () => {
  const original=globalThis.fetch;
  try {
    globalThis.fetch=async()=>new Response('data: {"type":"error","code":"provider_timeout","message":"Timed out"}\n\ndata: {"type":"token","content":"Must not appear"}\n\n');
    const events=[];
    for await(const event of streamQuery('question','test-token')) events.push(event);
    assert.deepEqual(events,[{type:'error',code:'provider_timeout',message:'Timed out'}]);
  } finally {globalThis.fetch=original;}
});

test('retry restores the question rather than a pasted provider failure', async () => {
  const {isAppFailureText,lastOriginalQuestion}=await import('../lib/chat-history.ts');
  const error="An answer was generated but the source-support check could not finish. The selected model's provider has reached a rate or quota limit. Wait before retrying or select another configured model.";
  assert.equal(isAppFailureText(error),true);
  assert.equal(isAppFailureText('Why does Groq return a rate limit error?'),false);
  assert.equal(lastOriginalQuestion([
    {role:'user',content:'When is the Agent Dispatcher allowed to act?'},
    {role:'user',content:error},
    {role:'assistant',content:"I don't have enough information."},
  ]),'When is the Agent Dispatcher allowed to act?');
  assert.equal(lastOriginalQuestion([{role:'user',content:error}]),null);
  assert.equal(isSavedChatMessage({role:'assistant',content:error}),false);
});
