'use client'

import { useState } from 'react'

interface CheckoutButtonProps {
    productId: string // Product ID is required
    className?: string
    children?: React.ReactNode
}

export default function CheckoutButton({ productId, className, children }: CheckoutButtonProps) {
    const [loading, setLoading] = useState(false)

    const handleCheckout = async () => {
        setLoading(true)
        // Redirect to checkout API with product ID as query parameter
        window.location.href = `/api/checkout?productId=${productId}`
    }

    return (
        <button
            onClick={handleCheckout}
            disabled={loading}
            className={className}
        >
            {loading ? 'Loading...' : children || 'Subscribe'}
        </button>
    )
}
