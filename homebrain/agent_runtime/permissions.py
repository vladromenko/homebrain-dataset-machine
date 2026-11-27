"""One model pool, distinct bounded tool authority for each role."""
ROLE_TOOLS = {
    'coordinator': {'status', 'receipt', 'delegate', 'memory', 'operation'},
    'dataset': {'receipt', 'search', 'read', 'git', 'status'},
    'hardware': {'status', 'search', 'read', 'vision'},
    'code': {'search', 'read', 'git', 'check', 'status'},
    'learning': {'status', 'receipt', 'search', 'read', 'git'},
    'knowledge': {'search', 'read', 'memory', 'status'},
}
