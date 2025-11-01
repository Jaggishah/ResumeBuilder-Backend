"""
Credit management service for AI features
"""
from fastapi import HTTPException, status
from database.models import User, SubscriptionType
from typing import Dict, Any


class CreditManager:
    """Manage user credits and subscription limits"""
    
    # Credit costs for different AI operations
    CREDIT_COSTS = {
        "enhance": 1,
        "analyze": 2,
        "generate": 3,
        "optimize": 1
    }
    
    # Credit limits per subscription type
    SUBSCRIPTION_LIMITS = {
        SubscriptionType.TRIAL: 10,
        SubscriptionType.BASIC: 100,
        SubscriptionType.PREMIUM: 500,
        SubscriptionType.PRO: -1  # Unlimited
    }
    
    @staticmethod
    async def check_and_use_credits(user: User, operation: str) -> bool:
        """
        Check if user has enough credits and deduct them
        Returns True if successful, raises HTTPException if insufficient credits
        """
        cost = CreditManager.CREDIT_COSTS.get(operation, 1)
        
        # Check if user has unlimited credits (PRO subscription)
        if user.subscription_type == SubscriptionType.PRO:
            # Still track usage for analytics
            user.credits_used += cost
            await user.save()
            return True
        
        # Check if user has enough credits
        if not user.has_credits(cost):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "message": "Insufficient credits",
                    "credits_remaining": user.credits_remaining,
                    "credits_needed": cost,
                    "subscription_type": user.subscription_type
                }
            )
        
        # Deduct credits
        success = await user.use_credit(cost)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Failed to deduct credits"
            )
        
        return True
    
    @staticmethod
    def get_subscription_info(user: User) -> Dict[str, Any]:
        """Get user's subscription and credit information"""
        return {
            "subscription_type": user.subscription_type,
            "credits_remaining": user.credits_remaining,
            "credits_used": user.credits_used,
            "is_unlimited": user.subscription_type == SubscriptionType.PRO,
            "subscription_start_date": user.subscription_start_date,
            "subscription_end_date": user.subscription_end_date
        }
    
    @staticmethod
    async def refund_credits(user: User, operation: str) -> bool:
        """
        Refund credits if operation fails
        """
        cost = CreditManager.CREDIT_COSTS.get(operation, 1)
        
        if user.subscription_type != SubscriptionType.PRO:
            await user.add_credits(cost)
            user.credits_used = max(0, user.credits_used - cost)
            await user.save()
        
        return True