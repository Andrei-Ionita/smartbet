import { Checkout } from '@polar-sh/nextjs'

// The Checkout function from @polar-sh/nextjs creates a route handler for GET requests
// It redirects users to the Polar.sh checkout page for the specified product

export const GET = Checkout({
    accessToken: process.env.POLAR_ACCESS_TOKEN,
    successUrl: `${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/dashboard?payment=success`,
    server: 'production', // or 'sandbox' for testing
})
