const accountFeaturesEnabled =
  process.env.NEXT_PUBLIC_ACCOUNT_FEATURES_ENABLED === 'enabled'
const commercialMode =
  process.env.NEXT_PUBLIC_COMMERCIAL_MODE === 'commercial'

if (accountFeaturesEnabled || commercialMode) {
  console.error('Free public launch is not cleared because commercial features are enabled.')
  console.error('Keep NEXT_PUBLIC_ACCOUNT_FEATURES_ENABLED and NEXT_PUBLIC_COMMERCIAL_MODE unset for the free, accountless launch.')
  console.error('Run npm run monetization:check before enabling accounts, email collection or payments.')
  process.exit(1)
}

console.log('Free public launch mode is correctly fail-closed: account features and payments are disabled.')
console.log('Operator, jurisdiction and legal-review fields are deferred to the monetization gate.')
