const required = {
  NEXT_PUBLIC_OPERATOR_NAME: process.env.NEXT_PUBLIC_OPERATOR_NAME,
  NEXT_PUBLIC_OPERATOR_ADDRESS: process.env.NEXT_PUBLIC_OPERATOR_ADDRESS,
  NEXT_PUBLIC_OPERATOR_COUNTRY: process.env.NEXT_PUBLIC_OPERATOR_COUNTRY,
  NEXT_PUBLIC_GOVERNING_LAW: process.env.NEXT_PUBLIC_GOVERNING_LAW,
  NEXT_PUBLIC_COMPETENT_COURTS: process.env.NEXT_PUBLIC_COMPETENT_COURTS,
}

const confirmations = {
  CONTACT_EMAILS_MONITORED: process.env.CONTACT_EMAILS_MONITORED,
  LEGAL_REVIEW_CONFIRMED: process.env.LEGAL_REVIEW_CONFIRMED,
}

const missing = Object.entries(required)
  .filter(([, value]) => !value?.trim())
  .map(([name]) => name)

const unconfirmed = Object.entries(confirmations)
  .filter(([, value]) => value?.trim().toLowerCase() !== 'confirmed')
  .map(([name]) => name)

if (missing.length || unconfirmed.length) {
  console.error('Monetization is not cleared.')
  if (missing.length) console.error(`Missing public legal fields: ${missing.join(', ')}`)
  if (unconfirmed.length) console.error(`Required confirmations: ${unconfirmed.join(', ')}=confirmed`)
  console.error('Do not enable accounts, email collection or payments until this check passes.')
  process.exit(1)
}

console.log('Operator identity, jurisdiction, monitored contacts and legal-review confirmations are present.')
