export function generateMatchSlug(homeTeam: string, awayTeam: string, date: string, id: number, leagueName: string): string {
    const sanitize = (str: string) =>
        str.toLowerCase()
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-+|-+$/g, '');

    const league = sanitize(leagueName);
    const home = sanitize(homeTeam);
    const away = sanitize(awayTeam);
    const dateStr = date.split('T')[0]; // Ensure YYYY-MM-DD

    return `/prediction/${league}/${home}-vs-${away}-${dateStr}-${id}`;
}

export function extractIdFromSlug(slug: string[]): number | null {
    // slug is an array due to [...slug] catch-all route
    // Expected format: ['league-name', 'home-vs-away-date-ID']

    if (!slug || slug.length < 2) return null;

    const lastSegment = slug[slug.length - 1];
    const parts = lastSegment.split('-');
    const id = parseInt(parts[parts.length - 1]);

    return isNaN(id) ? null : id;
}

export function generateSchemaLD(fixture: any) {
    if (!fixture) return null;

    const homeTeam = fixture.home_team;
    const awayTeam = fixture.away_team;
    const startTime = fixture.kickoff;
    // Use a default end time of +2 hours if not available
    const endTime = new Date(new Date(startTime).getTime() + 2 * 60 * 60 * 1000).toISOString();

    const schema = {
        "@context": "https://schema.org",
        "@type": "SportsEvent",
        "name": `${homeTeam} vs ${awayTeam}`,
        "description": `Football prediction and betting tips for ${homeTeam} vs ${awayTeam} in ${fixture.league}.`,
        "startDate": startTime,
        "endDate": endTime,
        "competitor": [
            {
                "@type": "SportsTeam",
                "name": homeTeam
            },
            {
                "@type": "SportsTeam",
                "name": awayTeam
            }
        ],
        "location": {
            "@type": "Place",
            "name": "Stadium" // Could be enriched if we had stadium data
        }
    };

    return schema;
}
