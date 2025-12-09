// using native fetch
// Actually, assume node 18+ is available which has native global fetch
(async () => {
    try {
        console.log('Fetching...');
        const res = await fetch('http://localhost:3000/api/recommendations');
        console.log('Status:', res.status);
        const text = await res.text();
        console.log('Body:', text);
    } catch (e) {
        console.error('Fetch error:', e);
    }
})();
