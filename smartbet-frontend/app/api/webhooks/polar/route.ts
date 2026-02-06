import { Webhooks } from '@polar-sh/nextjs'
import { NextResponse } from 'next/server'

// This webhook handler processes events from Polar.sh
// When a subscription is created/updated, it will update the user's tier

export const POST = Webhooks({
    webhookSecret: process.env.POLAR_WEBHOOK_SECRET || '',
    onPayload: async (payload) => {
        console.log('Received Polar webhook:', payload.type)

        // Handle different event types
        switch (payload.type) {
            case 'subscription.created':
            case 'subscription.updated':
                // Extract customer email from the subscription
                const subscription = payload.data
                const customerEmail = subscription.customer?.email

                if (customerEmail) {
                    console.log(`Upgrading user ${customerEmail} to Pro`)

                    // Call your Django backend to update user tier
                    try {
                        const response = await fetch(`${process.env.DJANGO_API_URL || 'http://localhost:8000'}/api/auth/upgrade-tier/`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Authorization': `Bearer ${process.env.POLAR_ACCESS_TOKEN}`, // For internal auth
                            },
                            body: JSON.stringify({
                                email: customerEmail,
                                tier: 'pro',
                                subscription_id: subscription.id,
                            }),
                        })

                        if (!response.ok) {
                            console.error('Failed to upgrade user tier:', await response.text())
                        }
                    } catch (error) {
                        console.error('Error calling Django API:', error)
                    }
                }
                break

            case 'subscription.canceled':
                // Handle subscription cancellation - downgrade to free
                const canceledSub = payload.data
                const canceledEmail = canceledSub.customer?.email

                if (canceledEmail) {
                    console.log(`Downgrading user ${canceledEmail} to Free`)

                    try {
                        await fetch(`${process.env.DJANGO_API_URL || 'http://localhost:8000'}/api/auth/upgrade-tier/`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                email: canceledEmail,
                                tier: 'free',
                            }),
                        })
                    } catch (error) {
                        console.error('Error downgrading user:', error)
                    }
                }
                break

            default:
                console.log('Unhandled webhook event:', payload.type)
        }
    },
})
