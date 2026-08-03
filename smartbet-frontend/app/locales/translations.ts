export type Language = 'en' | 'ro'

export const translations = {
    en: {
        nav: {
            home: 'Home',
            dashboard: 'Dashboard',
            explore: 'Explore',
            monitoring: 'Model monitoring',
            trackRecord: 'Verified record',
            bankroll: 'Bankroll',
            pricing: 'Pricing',
            upgradeToPro: 'Upgrade to Pro',
            login: 'Login',
            signup: 'Sign Up',
            logout: 'Logout',
            profile: 'Profile'
        },
        common: {
            loading: 'Loading...',
            error: 'An error occurred',
            retry: 'Retry',
            viewAnalysis: 'View Analysis',
            search: 'Search'
        },
        landing: {
            heroTitle: 'BetGlitch.',
            heroTitleHighlight: 'Not Guesswork.',
            heroSubtitle: 'Football model signals with a record you can verify. Selected picks are frozen before kickoff and stay public after settlement.',
            exploreButton: 'Explore Predictions',
            stats: {
                accuracy: 'Accuracy',
                roi: 'Avg ROI',
                coverage: 'Leagues',
                topPicksToday: 'Top Picks Today',
                confidenceThreshold: 'Confidence Threshold',
                totalFixtures: 'Total Fixtures',
                highestConfidence: 'Highest Confidence',
                daysAhead: 'Days Ahead',
                aiEnsemble: 'AI Ensemble'
            },
            trackRecord: 'Track Record',
            learnMore: 'Learn More',
            featuredBadge: 'Featured Picks',
            topRecsTitle: "Today's Top Recommendations",
            topRecsSubtitle: 'Hand-picked predictions with the highest confidence scores and expected value',
            featured: 'Featured Recommendations',
            refreshTimer: 'Updates in',
            noBets: 'No high-confidence predictions available right now.',
            features: {
                title: 'Why Choose BetGlitch?',
                subtitle: 'Stop wasting time on manual research. Bet on Value, instantly.',
                f1Title: 'Read the model, not a tip',
                f1Desc: "We analyze 2,000+ matches so you don't have to. We deliver only the top opportunities, saving you hours of research every week.",
                f2Title: 'Transparent Track Record',
                f2Desc: 'We track every recommendation. Wins and losses. No deleting history. Pure accountability.',
                f3Title: 'Bankroll Protection',
                f3Desc: "We don't just tell you WHO to bet on. We tell you HOW MUCH to bet using the Kelly Criterion."
            }
        },
        dashboard: {
            title: 'My Dashboard',
            subtitle: 'Welcome back to your betting command center',
            manageBankroll: 'Manage Bankroll',
            smartPicks: 'Smart Recommendations',
            modelPerformance: {
                title: 'Model Performance',
                subtitle: 'Transparency is our core value. See how our models are performing.',
                viewAuditLog: 'View Full History'
            }
        },
        card: {
            recentForm: 'Recent Form',
            expectedValue: 'Expected Value',
            confidence: 'Confidence',
            bestOdds: 'Best Odds',
            liveOdds: 'Live Odds Available',
            opportunity: 'Opportunity Assessment',
            viewAnalysis: 'View Analysis',
            hideAnalysis: 'Hide Analysis',
            analysisPending: {
                title: 'Analysis Pending',
                desc: 'Our AI models are currently analyzing this fixture.'
            },
            risk: {
                title: 'Risk Factors Present',
                advice: 'Consider: Reduced stake, skip if uncertain'
            },
            stake: {
                title: 'Recommended Stake',
                calculate: 'Calculate Stake'
            },
            analysis: {
                title: 'Betting Analysis',
                quickInsights: 'Quick Insights',
                whyPrediction: 'Why This Prediction?',
                predictionStrength: 'Prediction Strength',
                marketConsensus: 'Market Consensus',
                bettingEdge: 'Betting Edge',
                predictionSummary: 'Prediction Summary',
                optimalBetSize: 'Optimal Bet Size (Kelly Criterion)',
                basedOnBankroll: 'Based on $1000 bankroll',
                highConfidence: 'High Confidence',
                mediumConfidence: 'Medium Confidence',
                lowConfidence: 'Low Confidence',
                unknownAgreement: 'Unknown',
                modelAgreementAnalysis: 'Model agreement analysis',
                multipleModelAnalysis: 'Multiple model analysis',
                excellentValue: 'Excellent Value',
                goodValue: 'Good Value',
                marginalValue: 'Marginal Value',
                poorValue: 'Poor Value',
                negativeEdge: 'Negative Edge',
                edge: 'Edge'
            },
            outcomes: {
                home: 'Home',
                draw: 'Draw',
                away: 'Away'
            },
            badges: {
                recommended: 'RECOMMENDED',
                premium: 'Premium',
                strong: 'Strong',
                highValue: 'High Value',
                goodValue: 'Good Value',
                valuePlay: 'Value Play',
                speculative: 'Speculative',
                veryStrong: 'Very Strong',
                moderate: 'Moderate',
                weak: 'Weak',
                strongSignal: 'Strong Signal',
                goodSignal: 'Good Signal',
                moderateSignal: 'Moderate Signal',
                weakSignal: 'Weak Signal',
                safe_pick: 'Safe Pick',
                value_bet: 'Value Bet'
            },
            riskMessages: {
                lowerConfidence: '• Lower confidence ({0}%) - higher uncertainty',
                lowEV: '• Low expected value ({0}%) - small edge',
                drawPrediction: '• Draw prediction - historically harder to predict accurately'
            },
            multiMarket: {
                bestMarket: 'Best',
                allMarkets: 'All Markets',
                options: 'options',
                markets: {
                    '1x2': 'Match Result',
                    'btts': 'Both Teams Score',
                    'over_under_2.5': 'O/U 2.5 Goals',
                    'double_chance': 'Double Chance'
                },
                shortNames: {
                    '1x2': '1X2',
                    'btts': 'BTTS',
                    'over_under_2.5': 'O/U 2.5',
                    'double_chance': 'DC'
                },
                starBest: '★ Best',
                notRecommended: 'Not recommended'
            }
        },
        trackRecord: {
            title: 'Verified record',
            subtitle: 'Settled published picks — the ones BetGlitch froze before kickoff. Wins and losses both.',
            disclaimer: 'Only settled published picks count towards these figures.',
            updateResults: 'Update Results',
            updating: 'Updating...',
            stats: {
                overallAccuracy: 'Overall Accuracy',
                winRate: 'Win Rate',
                roi: 'ROI ($10/bet)',
                totalTracked: 'Total Tracked',
                predictionsLogged: 'Predictions logged',
                accuracyByType: 'Accuracy by Prediction Type',
                homeWins: 'Home Wins',
                draws: 'Draws',
                awayWins: 'Away Wins'
            },
            filters: {
                label: 'Filters:',
                allLeagues: 'All Leagues',
                completedOnly: 'Completed Only',
                all: 'All (Including Pending)',
                showing: 'Showing {0} predictions',
                dateFrom: 'From',
                dateTo: 'To',
                allResults: 'All Results',
                winsOnly: 'Wins Only',
                lossesOnly: 'Losses Only',
                allOutcomes: 'All Outcomes',
                clearFilters: 'Clear Filters',
                activeFilters: '{0} active'
            },
            table: {
                match: 'Match',
                predicted: 'Predicted',
                actual: 'Actual',
                result: 'Result',
                confidence: 'Confidence',
                ev: 'EV',
                pl: 'P/L ($10)',
                date: 'Date',
                score: 'Score:',
                pending: 'Pending',
                noPredictions: 'No predictions found'
            },
            transparency: {
                title: '🔒 Our Transparency Commitment',
                whatWeTrack: '📋 What We Track',
                whatWeTrackDesc: 'Public performance is measured only on published picks — the ones BetGlitch froze before kickoff with their recorded odds and bookmaker. The log below also shows earlier predictions, clearly marked as legacy and excluded from every figure.',
                why: 'Why?',
                whyDesc: 'Because a record is only meaningful if it cannot be edited afterwards. Only published picks — frozen before kickoff — count towards public performance.',
                points: {
                    timestamped: 'Timestamped BEFORE kickoff',
                    timestampedDesc: 'A published pick records its selection, odds, bookmaker and time before the match starts, and settlement grades that frozen copy',
                    verified: 'Third-party verified',
                    verifiedDesc: 'Match outcomes come from an independent data provider rather than being self-reported',
                    permanent: 'Never deleted',
                    permanentDesc: 'Historical data is permanent - we show both wins and losses',
                    history: 'Nothing is deleted',
                    historyDesc: 'Earlier predictions stay visible as legacy even though they cannot count towards the verified record',
                    updates: 'Real-time updates',
                    updatesDesc: 'Click "Update Results" to fetch the latest match outcomes'
                },
                note: 'Note:',
                noteDesc: 'Only published picks enter the verified record. Live model signals shown elsewhere in the product are not counted, and a published pick is never withdrawn or re-graded once it settles.'
            }
        },
        monitoring: {
            title: 'Official Results',
            subtitle: 'Transparent tracking of our prediction accuracy and history',
            tabs: {
                dashboard: 'Model Performance',
                accuracy: 'Detailed Accuracy',
                recommended: 'Recommendation History',
                analytics: 'Analytics',
                settings: 'Settings'
            },
            whyTrack: {
                title: 'Why We Track Performance',
                description: 'Transparency is our core value. We believe you should know exactly how our models perform before you place a bet. That\'s why we track every single recommendation we make, win or lose.'
            },
            analytics: {
                title: 'Analytics Dashboard',
                comingSoon: 'Analytics Coming Soon',
                description: 'Advanced analytics including trend analysis, usage patterns, and performance insights will be available here.'
            },
            settings: {
                title: 'Monitoring Settings',
                autoRefresh: 'Auto-refresh Interval',
                alerts: 'Enable performance alerts',
                logging: 'Enable detailed logging',
                errorTracking: 'Enable error tracking',
                seconds: '{0} seconds',
                minute: '1 minute'
            }
        },
        bankroll: {
            title: 'Set Up Your Bankroll',
            subtitle: 'Manage your betting budget responsibly with our bankroll management system',
            form: {
                initialBankroll: 'Initial Bankroll',
                initialBankrollHelp: "Amount you're willing to allocate for betting",
                riskProfile: 'Risk Profile',
                stakingStrategy: 'Staking Strategy',
                dailyLossLimit: 'Daily Loss Limit (Optional)',
                dailyLossLimitHelp: 'Max loss allowed per day',
                weeklyLossLimit: 'Weekly Loss Limit (Optional)',
                weeklyLossLimitHelp: 'Max loss allowed per week',
                maxStake: 'Max Stake per Bet (% of Bankroll)',
                maxStakeHelp: 'Maximum percentage of bankroll to stake on a single bet (1-25%)',
                autoCalculated: 'Auto-calculated',
                cancel: 'Cancel',
                create: 'Create Bankroll',
                creating: 'Creating...'
            },
            riskProfiles: {
                conservative: {
                    label: 'Conservative',
                    description: 'Safest approach with small stakes and high confidence requirements'
                },
                balanced: {
                    label: 'Balanced',
                    description: 'Balanced approach suitable for most bettors'
                },
                aggressive: {
                    label: 'Aggressive',
                    description: 'Higher risk/reward for experienced bettors'
                }
            },
            strategies: {
                kelly_fractional: {
                    label: 'Fractional Kelly (1/4)',
                    description: 'Recommended: Safer version of Kelly Criterion'
                },
                kelly: {
                    label: 'Full Kelly Criterion',
                    description: 'Aggressive: Mathematical optimal but high variance'
                },
                fixed_percentage: {
                    label: 'Fixed Percentage',
                    description: 'Bet same % of bankroll every time'
                },
                fixed_amount: {
                    label: 'Fixed Amount',
                    description: 'Bet same dollar amount every time'
                }
            },
            page: {
                title: 'Betting Budget & Bankroll',
                subtitle: 'Track your betting financial health and performance',
                currentBalance: 'Current Balance',
                totalProfit: 'Total Profit',
                roi: 'Return on Investment',
                activeBets: 'Active Bets Value',
                transactionHistory: 'Transaction History',
                noTransactions: 'No transactions recorded yet',
                manageBankroll: 'Manage Bankroll Setting',
                stats: {
                    title: 'Performance Statistics',
                    totalBets: 'Total Bets',
                    winRate: 'Win Rate',
                    avgProfit: 'Avg Profit/Bet',
                    pending: 'Pending',
                    atRisk: 'at risk'
                },
                limits: {
                    title: 'Loss Limits',
                    daily: 'Daily Limit',
                    weekly: 'Weekly Limit',
                    reached: 'limit reached - betting paused'
                },
                transactions: {
                    recent: 'Recent Transactions',
                    all: 'All Transactions',
                    viewAll: 'View All →',
                    table: {
                        match: 'Match',
                        outcome: 'Outcome',
                        odds: 'Odds',
                        stake: 'Stake',
                        pl: 'P/L',
                        status: 'Status',
                        date: 'Date'
                    }
                },
                settings: {
                    title: 'Bankroll Settings',
                    accountCreated: 'Account created'
                }
            }
        },
        beta: {
            heading: 'BetGlitch Public Beta — free while we build the verified public record',
            badge: 'Free public beta',
            account: 'An account is free and needs no payment method.',
            supporting: 'You can use every public surface without paying: live model signals, the verified record and every published proof page.',
            meansTitle: 'What this means today',
            m1: 'Access is currently free — there is nothing to buy.',
            m2: 'No payment method is required, and none is collected.',
            m3: 'Commercial plans may be introduced after we have validated the record.',
            m4: 'If that changes, beta users will be told before it does.',
            createAccount: 'Create a free account',
            seeRecord: 'See the verified record'
        },
        explore: {
            title: 'Explore live football signals',
            subtitle: 'Search upcoming fixtures and inspect current model scores, market signals and recorded odds. Live signals can update before kickoff and are not part of the verified record unless BetGlitch publishes an immutable claim.',
            results: 'Search Results',
            howTo: {
                title: 'How to Use the Explorer',
                step1Title: 'Search',
                step1Body: 'Enter a team, league or country to find upcoming fixtures',
                step2Title: 'Inspect',
                step2Body: 'Open a fixture to see its model score, market signal and recorded odds',
                step3Title: 'Decide for yourself',
                step3Body: 'A model score ranks relative confidence — it is not a calibrated probability'
            },
            search: {
                placeholder: "Search by team name (e.g., 'Manchester City', 'Barcelona', 'Bayern')",
                allLeagues: 'All Leagues',
                features: {
                    leagues: 'Search across all 27 leagues',
                    odds: 'Real-time odds',
                    predictions: 'AI predictions'
                },
                loading: 'Searching fixtures...',
                noResults: 'No matches found',
                tryStandard: 'Try using standard team names (e.g., use "Man City" instead of "City")',
                initialState: 'Search for any upcoming match to see AI predictions'
            },
            browse: {
                title: 'Upcoming Fixtures',
                loading: 'Loading fixtures...',
                noFixtures: 'No upcoming fixtures found for this league',
                selectLeague: 'Select a league to browse upcoming fixtures'
            },
            analysis: {
                title: 'Match Analysis',
                loading: 'Generating AI analysis...',
                error: 'Failed to load analysis',
                back: 'Back to results'
            }
        }
    },
    ro: {
        nav: {
            home: 'Acasă',
            dashboard: 'Panou Control',
            explore: 'Explorează',
            monitoring: 'Monitorizare model',
            trackRecord: 'Istoric verificat',
            bankroll: 'Buget',
            pricing: 'Prețuri',
            upgradeToPro: 'Treci la Pro',
            login: 'Autentificare',
            signup: 'Înregistrare',
            logout: 'Deconectare',
            profile: 'Profil'
        },
        common: {
            loading: 'Se încarcă...',
            error: 'A apărut o eroare',
            retry: 'Reîncearcă',
            viewAnalysis: 'Vezi Analiza',
            search: 'Caută'
        },
        landing: {
            heroTitle: 'Pariază Inteligent.',
            heroTitleHighlight: 'Nu la Ghici.',
            heroSubtitle: 'Semnale de model pentru fotbal, cu un istoric pe care îl poți verifica. Pontajele selectate sunt înghețate înainte de start și rămân publice după încheiere.',
            exploreButton: 'Explorează Predicții',
            stats: {
                accuracy: 'Acuratețe',
                roi: 'ROI Mediu',
                coverage: 'Ligi',
                topPicksToday: 'Topul Zilei',
                confidenceThreshold: 'Prag Încredere',
                totalFixtures: 'Total Meciuri',
                highestConfidence: 'Încredere Maximă',
                daysAhead: 'Zile în Avans',
                aiEnsemble: 'Ansamblu AI'
            },
            trackRecord: 'Istoric Performanță',
            learnMore: 'Află Mai Multe',
            featuredBadge: 'Ponturi Recomandate',
            topRecsTitle: 'Recomandările de Top de Astăzi',
            topRecsSubtitle: 'Predicții selectate cu cele mai mari scoruri de încredere și valoare așteptată',
            featured: 'Recomandări Top',
            refreshTimer: 'Actualizare în',
            noBets: 'Nu există predicții cu grad ridicat de încredere momentan.',
            features: {
                title: 'De ce BetGlitch?',
                subtitle: "Nu mai pierde ore întregi analizând manual. Pariază pe Valoare, instant.",
                f1Title: 'Citește modelul, nu un pont',
                f1Desc: 'Analizăm 2.000+ meciuri în locul tău. Tu primești direct selecția finală de top, economisind zeci de ore de documentare săptămânal.',
                f2Title: 'Istoric 100% Transparent',
                f2Desc: 'Monitorizăm fiecare recomandare. Câștiguri și pierderi. Fără istoric șters. Responsabilitate totală.',
                f3Title: 'Protecția Bugetului',
                f3Desc: 'Nu îți spunem doar PE CINE să pariezi. Îți spunem CÂT să pariezi folosind criteriul Kelly pentru a-ți proteja banii.'
            }
        },
        dashboard: {
            title: 'Panoul Meu',
            subtitle: 'Bine ai revenit la portalul tău de pariuri',
            manageBankroll: 'Gestionează Buget',
            smartPicks: 'Recomandări Inteligente',
            modelPerformance: {
                title: 'Performanță Model',
                subtitle: 'Transparența este valoarea noastră. Vezi cum performează modelele.',
                viewAuditLog: 'Vezi Istoric Complet'
            }
        },
        card: {
            recentForm: 'Forma Recentă',
            expectedValue: 'Valoare Așteptată',
            confidence: 'Încredere',
            bestOdds: 'Cote Top',
            liveOdds: 'Cote Live Disponibile',
            opportunity: 'Evaluare Oportunitate',
            viewAnalysis: 'Vezi Analiza',
            hideAnalysis: 'Ascunde Analiza',
            analysisPending: {
                title: 'Analiză în Curs',
                desc: 'Modelele noastre AI analizează acest meci.'
            },
            risk: {
                title: 'Factori de Risc',
                advice: 'Sfat: miză redusă sau evită dacă nu ești sigur'
            },
            stake: {
                title: 'Miză Recomandată',
                calculate: 'Calculează Miza'
            },
            analysis: {
                title: 'Analiză Pariuri',
                quickInsights: 'Insight-uri Rapide',
                whyPrediction: 'De ce această predicție?',
                predictionStrength: 'Putere Predicție',
                marketConsensus: 'Consens Piață',
                bettingEdge: 'Avantaj Pariu',
                predictionSummary: 'Rezumat Predicție',
                optimalBetSize: 'Miză Optimă (Criteriu Kelly)',
                basedOnBankroll: 'Bazat pe buget de $1000',
                highConfidence: 'Încredere Ridicată',
                mediumConfidence: 'Încredere Medie',
                lowConfidence: 'Încredere Scăzută',
                unknownAgreement: 'Necunoscut',
                modelAgreementAnalysis: 'Analiză acord modele',
                multipleModelAnalysis: 'Analiză modele multiple',
                excellentValue: 'Valoare Excelentă',
                goodValue: 'Valoare Bună',
                marginalValue: 'Valoare Marginală',
                poorValue: 'Valoare Slabă',
                negativeEdge: 'Avantaj Negativ',
                edge: 'Avantaj'
            },
            outcomes: {
                home: 'Gazde',
                draw: 'Egal',
                away: 'Oaspeți'
            },
            badges: {
                recommended: 'RECOMANDAT',
                premium: 'Premium',
                strong: 'Puternic',
                highValue: 'Valoare Mare',
                goodValue: 'Valoare Bună',
                valuePlay: 'Joc Valoare',
                speculative: 'Speculativ',
                veryStrong: 'Foarte Puternic',
                moderate: 'Moderat',
                weak: 'Slab',
                strongSignal: 'Semnal Puternic',
                goodSignal: 'Semnal Bun',
                moderateSignal: 'Semnal Moderat',
                weakSignal: 'Semnal Slab',
                safe_pick: 'Pariu Sigur',
                value_bet: 'Pariu de Valoare'
            },
            riskMessages: {
                lowerConfidence: '• Încredere mai mică ({0}%) - incertitudine mai mare',
                lowEV: '• Valoare așteptată mică ({0}%) - avantaj redus',
                drawPrediction: '• Predicție de egalitate - istoric mai greu de prezis'
            },
            multiMarket: {
                bestMarket: 'Cel mai bun',
                allMarkets: 'Toate Piețele',
                options: 'opțiuni',
                markets: {
                    '1x2': 'Rezultat Final',
                    'btts': 'Ambele Marchează',
                    'over_under_2.5': 'Peste/Sub 2.5',
                    'double_chance': 'Șansă Dublă'
                },
                shortNames: {
                    '1x2': '1X2',
                    'btts': 'GG/NG',
                    'over_under_2.5': 'P/S 2.5',
                    'double_chance': 'ȘD'
                },
                starBest: '★ Cel mai bun',
                notRecommended: 'Nerecomandat'
            }
        },
        trackRecord: {
            title: 'Istoric verificat',
            subtitle: 'Pontaje publicate încheiate — cele înghețate de BetGlitch înainte de start. Și câștiguri, și pierderi.',
            disclaimer: 'Doar pontajele publicate încheiate contează pentru aceste cifre.',
            updateResults: 'Actualizează Rezultate',
            updating: 'Se actualizează...',
            stats: {
                overallAccuracy: 'Acuratețe Generală',
                winRate: 'Rată de Câștig',
                roi: 'ROI ($10/pariu)',
                totalTracked: 'Total Urmărite',
                predictionsLogged: 'Predicții înregistrate',
                accuracyByType: 'Acuratețe după Tip Predicție',
                homeWins: 'Victorii Gazde',
                draws: 'Egaluri',
                awayWins: 'Victorii Oaspeți'
            },
            filters: {
                label: 'Filtre:',
                allLeagues: 'Toate Ligile',
                completedOnly: 'Doar Finalizate',
                all: 'Toate (Inclusiv În Așteptare)',
                showing: 'Se afișează {0} predicții',
                dateFrom: 'De la',
                dateTo: 'Până la',
                allResults: 'Toate Rezultatele',
                winsOnly: 'Doar Câștiguri',
                lossesOnly: 'Doar Pierderi',
                allOutcomes: 'Toate Predicțiile',
                clearFilters: 'Șterge Filtre',
                activeFilters: '{0} active'
            },
            table: {
                match: 'Meci',
                predicted: 'Predicție',
                actual: 'Real',
                result: 'Rezultat',
                confidence: 'Încredere',
                ev: 'EV',
                pl: 'P/L ($10)',
                date: 'Dată',
                score: 'Scor:',
                pending: 'În Așteptare',
                noPredictions: 'Nu s-au găsit predicții'
            },
            transparency: {
                title: '🔒 Angajamentul Nostru de Transparență',
                whatWeTrack: '📋 Ce Urmărim',
                whatWeTrackDesc: 'Performanța publică se măsoară doar pe pontajele publicate — cele înghețate de BetGlitch înainte de start, cu cota și casa de pariuri înregistrate. Jurnalul de mai jos arată și predicții mai vechi, marcate clar ca legacy și excluse din orice cifră.',
                why: 'De ce?',
                whyDesc: 'Pentru că un istoric contează doar dacă nu poate fi editat ulterior. Doar pontajele publicate — înghețate înainte de start — contează pentru performanța publică.',
                points: {
                    timestamped: 'Marcate temporal ÎNAINTE de start',
                    timestampedDesc: 'Un pontaj publicat își înregistrează selecția, cota, casa de pariuri și ora înainte de startul meciului, iar decontarea evaluează exact acea copie înghețată',
                    verified: 'Verificate de terți',
                    verifiedDesc: 'Rezultatele meciurilor provin de la un furnizor de date independent, nu sunt raportate de noi',
                    permanent: 'Niciodată șterse',
                    permanentDesc: 'Datele istorice sunt permanente - arătăm atât câștigurile cât și pierderile',
                    history: 'Nimic nu se șterge',
                    historyDesc: 'Predicțiile mai vechi rămân vizibile ca legacy, chiar dacă nu pot conta în istoricul verificat',
                    updates: 'Actualizări în timp real',
                    updatesDesc: 'Apasă "Actualizează Rezultate" pentru a prelua cele mai recente rezultate ale meciurilor'
                },
                note: 'Notă:',
                noteDesc: 'Doar pontajele publicate intră în istoricul verificat. Semnalele live afișate în restul produsului nu sunt contorizate, iar un pontaj publicat nu este niciodată retras sau reevaluat după încheiere.'
            }
        },
        monitoring: {
            title: 'Rezultate Oficiale',
            subtitle: 'Urmărire transparentă a acurateței și istoricului nostru',
            tabs: {
                dashboard: 'Performanță Model',
                accuracy: 'Acuratețe Detaliată',
                recommended: 'Istoric Recomandări',
                analytics: 'Analitice',
                settings: 'Setări'
            },
            whyTrack: {
                title: 'De Ce Urmărim Performanța',
                description: 'Transparența este valoarea noastră fundamentală. Credem că ar trebui să știi exact cum performează modelele noastre înainte de a plasa un pariu. De aceea urmărim fiecare recomandare pe care o facem, câștigătoare sau pierzătoare.'
            },
            analytics: {
                title: 'Panou Analitice',
                comingSoon: 'Analitice Disponibile în Curând',
                description: 'Analize avansate inclusiv analiza tendințelor, modele de utilizare și insight-uri performanță vor fi disponibile aici.'
            },
            settings: {
                title: 'Setări Monitorizare',
                autoRefresh: 'Interval Actualizare Automată',
                alerts: 'Activează alerte performanță',
                logging: 'Activează jurnalizare detaliată',
                errorTracking: 'Activează urmărire erori',
                seconds: '{0} secunde',
                minute: '1 minut'
            }
        },
        bankroll: {
            title: 'Configurează Bugetul',
            subtitle: 'Gestionează-ți bugetul de pariuri responsabil cu sistemul nostru de management',
            form: {
                initialBankroll: 'Buget Inițial',
                initialBankrollHelp: 'Suma pe care ești dispus să o aloci pentru pariuri',
                riskProfile: 'Profil de Risc',
                stakingStrategy: 'Strategie de Mize',
                dailyLossLimit: 'Limită de Pierdere Zilnică (Opțional)',
                dailyLossLimitHelp: 'Pierderea maximă permisă pe zi',
                weeklyLossLimit: 'Limită de Pierdere Săptămânală (Opțional)',
                weeklyLossLimitHelp: 'Pierderea maximă permisă pe săptămână',
                maxStake: 'Miză Maximă per Pariu (% din Buget)',
                maxStakeHelp: 'Procentul maxim din buget de pariat pe un singur bilet (1-25%)',
                autoCalculated: 'Calculat automat',
                cancel: 'Anulează',
                create: 'Creează Buget',
                creating: 'Se creează...'
            },
            riskProfiles: {
                conservative: {
                    label: 'Conservator',
                    description: 'Abordare sigură cu mize mici și cerințe mari de încredere'
                },
                balanced: {
                    label: 'Echilibrat',
                    description: 'Abordare echilibrată potrivită pentru majoritatea pariorilor'
                },
                aggressive: {
                    label: 'Agresiv',
                    description: 'Risc/recompensă mai mare pentru pariori experimentați'
                }
            },
            strategies: {
                kelly_fractional: {
                    label: 'Kelly Fracționat (1/4)',
                    description: 'Recomandat: Versiune mai sigură a criteriului Kelly'
                },
                kelly: {
                    label: 'Criteriul Kelly Complet',
                    description: 'Agresiv: Optim matematic dar cu variație mare'
                },
                fixed_percentage: {
                    label: 'Procent Fix',
                    description: 'Pariază același % din buget de fiecare dată'
                },
                fixed_amount: {
                    label: 'Sumă Fixă',
                    description: 'Pariază aceeași sumă de fiecare dată'
                }
            },
            page: {
                title: 'Buget și Bankroll',
                subtitle: 'Urmărește sănătatea financiară și performanța pariurilor tale',
                currentBalance: 'Balanță Curentă',
                totalProfit: 'Profit Total',
                roi: 'Randament (ROI)',
                activeBets: 'Valoare Pariuri Active',
                transactionHistory: 'Istoric Tranzacții',
                noTransactions: 'Nu există tranzacții înregistrate',
                manageBankroll: 'Gestionează Setări Bankroll',
                stats: {
                    title: 'Statistici Performanță',
                    totalBets: 'Total Pariuri',
                    winRate: 'Rată Câștig',
                    avgProfit: 'Profit Mediu/Pariu',
                    pending: 'În Desfășurare',
                    atRisk: 'la risc'
                },
                limits: {
                    title: 'Limite de Pierdere',
                    daily: 'Limită Zilnică',
                    weekly: 'Limită Săptămânală',
                    reached: 'limită atinsă - pariere pusă pe pauză'
                },
                transactions: {
                    recent: 'Tranzacții Recente',
                    all: 'Toate Tranzacțiile',
                    viewAll: 'Vezi Toate →',
                    table: {
                        match: 'Meci',
                        outcome: 'Rezultat',
                        odds: 'Cote',
                        stake: 'Miză',
                        pl: 'P/L',
                        status: 'Status',
                        date: 'Dată'
                    }
                },
                settings: {
                    title: 'Setări Bankroll',
                    accountCreated: 'Cont creat'
                }
            }
        },
        beta: {
            heading: 'BetGlitch Beta Public — gratuit cât timp construim istoricul public verificat',
            badge: 'Beta public gratuit',
            account: 'Contul este gratuit și nu necesită nicio metodă de plată.',
            supporting: 'Poți folosi gratuit toate secțiunile publice: semnalele live ale modelului, istoricul verificat și fiecare pagină de dovadă publicată.',
            meansTitle: 'Ce înseamnă asta astăzi',
            m1: 'Accesul este gratuit în prezent — nu ai ce cumpăra.',
            m2: 'Nu se cere nicio metodă de plată și nu se colectează niciuna.',
            m3: 'Planuri comerciale pot fi introduse după ce validăm istoricul.',
            m4: 'Dacă acest lucru se schimbă, utilizatorii beta vor fi anunțați în prealabil.',
            createAccount: 'Creează un cont gratuit',
            seeRecord: 'Vezi istoricul verificat'
        },
        explore: {
            title: 'Explorează semnale de model pentru fotbal',
            subtitle: 'Caută meciuri viitoare și inspectează scorurile actuale ale modelului, semnalele de piață și cotele înregistrate. Semnalele live se pot modifica înainte de start și nu fac parte din istoricul verificat decât dacă BetGlitch publică o revendicare imuabilă.',
            results: 'Rezultatele căutării',
            howTo: {
                title: 'Cum folosești Exploratorul',
                step1Title: 'Caută',
                step1Body: 'Introdu o echipă, o ligă sau o țară pentru a găsi meciuri viitoare',
                step2Title: 'Inspectează',
                step2Body: 'Deschide un meci pentru a-i vedea scorul modelului, semnalul de piață și cotele înregistrate',
                step3Title: 'Decide singur',
                step3Body: 'Scorul modelului exprimă încrederea relativă — nu este o probabilitate calibrată'
            },
            search: {
                placeholder: "Caută după nume echipă (ex: 'FCSB', 'Real Madrid', 'Liverpool')",
                allLeagues: 'Toate Ligile',
                features: {
                    leagues: 'Caută în toate cele 27 de ligi',
                    odds: 'Cote în timp real',
                    predictions: 'Predicții AI'
                },
                loading: 'Se caută meciuri...',
                noResults: 'Nu s-au găsit meciuri',
                tryStandard: 'Încearcă să folosești nume standard de echipe',
                initialState: 'Caută orice meci viitor pentru a vedea predicțiile AI'
            },
            browse: {
                title: 'Meciuri Viitoare',
                loading: 'Se încarcă meciurile...',
                noFixtures: 'Nu s-au găsit meciuri viitoare pentru această ligă',
                selectLeague: 'Selectează o ligă pentru a vedea meciurile viitoare'
            },
            analysis: {
                title: 'Analiză Meci',
                loading: 'Se generează analiza AI...',
                error: 'Nu s-a putut încărca analiza',
                back: 'Înapoi la rezultate'
            }
        }
    }
}

export type Resources = typeof translations.en
