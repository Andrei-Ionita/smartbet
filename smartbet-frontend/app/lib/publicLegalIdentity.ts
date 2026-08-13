export const publicLegalIdentity = {
  operatorName: process.env.NEXT_PUBLIC_OPERATOR_NAME?.trim() || '',
  operatorAddress: process.env.NEXT_PUBLIC_OPERATOR_ADDRESS?.trim() || '',
  operatorCountry: process.env.NEXT_PUBLIC_OPERATOR_COUNTRY?.trim() || '',
  governingLaw: process.env.NEXT_PUBLIC_GOVERNING_LAW?.trim() || '',
  competentCourts: process.env.NEXT_PUBLIC_COMPETENT_COURTS?.trim() || '',
} as const

export type PublicLegalIdentityField = keyof typeof publicLegalIdentity

export const missingPublicLegalIdentityFields = (
  Object.entries(publicLegalIdentity) as Array<[PublicLegalIdentityField, string]>
)
  .filter(([, value]) => !value)
  .map(([field]) => field)

export const PUBLIC_LEGAL_IDENTITY_COMPLETE = missingPublicLegalIdentityFields.length === 0
