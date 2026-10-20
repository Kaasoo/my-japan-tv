const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { test } = require('node:test');

function app(navigator) {
    const nodes = new Map();
    const node = () => ({ children: [], style: {}, classList: { add() {}, remove() {} },
        appendChild(child) { this.children.push(child); }, setAttribute() {} });
    const document = {
        getElementById(id) { if (!nodes.has(id)) nodes.set(id, node()); return nodes.get(id); },
        createElement: node, querySelectorAll() { return []; }, addEventListener() {},
    };
    const context = vm.createContext({ navigator, document, console, navigations: [], opened: [],
        location: { assign(url) { context.navigations.push(url); } } });
    context.window = context;
    const scripts = [...fs.readFileSync('index.html', 'utf8').matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
    vm.runInContext(scripts.at(-1)[1], context);
    vm.runInContext(fs.readFileSync('channels.js', 'utf8'), context);
    vm.runInContext('openPlayer = (url, name) => opened.push({ url, name }); renderChannels();', context);
    const cards = document.getElementById('channel-list').children
        .filter(n => n.className === 'channel-grid').flatMap(n => n.children);
    return { context, cards };
}

test('Android Japan channel navigates in the same tab', () => {
    const { context, cards } = app({ userAgent: 'Mozilla/5.0 (Linux; Android 15) Chrome/130.0 Mobile' });
    cards[0].onclick();
    assert.equal(context.navigations[0], 'https://mov3.co/embednhk.html');
    assert.equal(context.opened.length, 0);
});

test('mobile client hints work with a reduced user agent', () => {
    const { context, cards } = app({ userAgent: 'Mozilla/5.0', userAgentData: { mobile: true } });
    cards[0].onclick();
    assert.equal(context.navigations.length, 1);
});

test('desktop retains its embedded player even on a narrow window', () => {
    const { context, cards } = app({ userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' });
    cards[0].onclick();
    assert.equal(context.navigations.length, 0);
    assert.equal(context.opened[0].name, 'NHK G');
});

test('mobile channels with native HLS still use the in-app player', () => {
    const { context, cards } = app({ userAgent: 'Android Mobile' });
    cards[6].onclick();
    assert.equal(context.navigations.length, 0);
    assert.equal(context.opened[0].name, 'NHK World');
});
