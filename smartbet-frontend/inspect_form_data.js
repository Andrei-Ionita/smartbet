
// Remove require, use global fetch
async function inspect() {
    try {
        const res = await fetch('http://localhost:3000/api/recommendations');
        const data = await res.json();
        if (data.recommendations && data.recommendations.length > 0) {
            console.log('--- Inspection of First Recommendation ---');
            console.log('Home Team:', data.recommendations[0].home_team);
            console.log('Teams Data:', JSON.stringify(data.recommendations[0].teams_data, null, 2));

            const homeForm = data.recommendations[0].teams_data?.home?.form;
            console.log('Home Form Raw:', homeForm, 'Type:', typeof homeForm);
            if (Array.isArray(homeForm)) console.log('Is Array with length:', homeForm.length);
        } else {
            console.log('No recommendations found.');
        }
    } catch (e) {
        console.error('Fetch failed:', e.message);
    }
}

inspect();
