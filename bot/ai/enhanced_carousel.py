"""
Enhanced Carousel Builder for Phase 6 Multi-Card Experience.

This module provides enhanced carousel building functions that support multi-card
selection with comparison features, AI insights, and intelligent product highlighting.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Dict, List, Any, Optional


def build_product_carousel(
    products: List[Dict], 
    comparison_table: Dict, 
    selection_reason: str,
    watch_id: int
) -> List[Dict]:
    """
    Build carousel of product cards with comparison context for Phase 6.
    
    Args:
    ----
        products: List of selected products
        comparison_table: Feature comparison data
        selection_reason: AI explanation for selection
        watch_id: Watch ID for click tracking
        
    Returns:
    -------
        List of product cards with comparison context
    """
    cards = []
    
    for i, product in enumerate(products):
        # Build enhanced card with differentiation highlights
        caption, keyboard = build_enhanced_card(
            product=product,
            position=i + 1,
            total_cards=len(products),
            comparison_table=comparison_table,
            watch_id=watch_id
        )
        
        cards.append({
            'caption': caption,
            'keyboard': keyboard,
            'image': product.get('image', ''),
            'asin': product.get('asin', ''),
            'type': 'product_card'
        })
    
    # Add comparison summary as final card if multiple products
    if len(products) > 1:
        summary_card = build_comparison_summary_card(
            comparison_table=comparison_table, 
            selection_reason=selection_reason,
            product_count=len(products)
        )
        cards.append(summary_card)
    
    return cards


def build_enhanced_card(
    product: Dict, 
    position: int, 
    total_cards: int,
    comparison_table: Dict,
    watch_id: int
) -> tuple[str, InlineKeyboardMarkup]:
    """
    Build an enhanced product card with AI insights and comparison highlights.
    
    Args:
    ----
        product: Product data
        position: Card position (1, 2, 3...)
        total_cards: Total number of cards
        comparison_table: Feature comparison data
        watch_id: Watch ID for tracking
        
    Returns:
    -------
        Tuple of (caption_text, keyboard_markup)
    """
    # Basic product info
    title = product.get('title', 'Unknown Product')
    price = product.get('price', 0)
    asin = product.get('asin', '')
    
    # Format price (convert from paise to rupees if needed)
    if price > 100000:  # Clearly in paise (>₹1000 in paise = ₹10+)
        price_rs = price // 100
    else:
        price_rs = price  # Already in rupees
    price_text = f"₹{price_rs:,}" if price > 0 else "Price unavailable"
    
    # Build caption with position indicator for multi-card
    if total_cards > 1:
        position_emoji = ["🥇", "🥈", "🥉"][position - 1] if position <= 3 else f"#{position}"
        caption = f"{position_emoji} **Option {position}**\n\n"
    else:
        caption = "🎯 **AI Best Match**\n\n"
    
    caption += f"📱 {title}\n💰 {price_text}\n\n"
    
    # Add AI insights and strengths
    strengths = comparison_table.get('strengths', {}).get(position - 1, [])
    if strengths:
        caption += "✨ **Best for**: " + ", ".join(strengths[:2]) + "\n\n"
    
    # Add feature highlights for multi-card
    if total_cards > 1:
        highlights = _get_product_highlights(product, position - 1, comparison_table)
        if highlights:
            caption += "🔍 **Key Features**:\n" + "\n".join(highlights) + "\n\n"
    
    # Call-to-action
    if total_cards > 1:
        caption += f"🔥 Tap to create watch for Option {position}!"
    else:
        caption += "🔥 Current best price - create watch now!"
    
    # Create button with callback data
    button_text = f"🛒 CREATE WATCH ({position})" if total_cards > 1 else "🛒 CREATE WATCH"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            text=button_text, 
            callback_data=f"click:{watch_id}:{asin}"
        )]
    ])
    
    return caption, keyboard


def build_comparison_summary_card(
    comparison_table: Dict, 
    selection_reason: str,
    product_count: int
) -> Dict:
    """
    Build a comparison summary card explaining the AI selection.
    
    Args:
    ----
        comparison_table: Feature comparison data
        selection_reason: AI explanation
        product_count: Number of products
        
    Returns:
    -------
        Summary card dict
    """
    caption = "🤖 **AI Comparison Summary**\n\n"
    
    # Add selection reason
    caption += f"📋 **Why these {product_count} options?**\n{selection_reason}\n\n"
    
    # Add key differences
    key_diffs = comparison_table.get('key_differences', [])
    if key_diffs:
        caption += "⚖️ **Key Differences**:\n"
        for diff in key_diffs[:3]:  # Show top 3 differences
            feature = diff['feature']
            values = diff['values']
            if len(set(values)) > 1:  # Only show if actually different
                caption += f"• **{feature}**: " + " vs ".join(values[:3]) + "\n"
        caption += "\n"
    
    # Add trade-offs if any
    trade_offs = comparison_table.get('trade_offs', [])
    if trade_offs:
        caption += "💡 **Trade-offs**:\n"
        for trade_off in trade_offs[:2]:  # Show top 2
            caption += f"• {trade_off}\n"
        caption += "\n"
    
    # Add recommendation
    caption += "💭 **Recommendation**: Review each option above and tap the one that best fits your needs!"
    
    return {
        'caption': caption,
        'keyboard': None,  # No button for summary card
        'image': '',
        'asin': '',
        'type': 'summary_card'
    }


def _get_product_highlights(product: Dict, product_index: int, comparison_table: Dict) -> List[str]:
    """Get key feature highlights for a product in comparison context."""
    highlights = []
    
    # Get key differences and highlight where this product stands out
    key_diffs = comparison_table.get('key_differences', [])
    
    for diff in key_diffs[:4]:  # Top 4 features
        feature = diff['feature']
        values = diff['values']
        
        if product_index < len(values):
            value = values[product_index]
            user_pref = diff.get('user_preference', '')
            
            # Highlight if this product has the best value
            best_index = diff.get('highlight_best', -1)
            if best_index == product_index:
                highlights.append(f"• **{feature}**: {value} ⭐")
            elif value and value != "Not specified":
                highlights.append(f"• **{feature}**: {value}")
    
    return highlights[:3]  # Limit to top 3 highlights


def build_ai_selection_message(
    presentation_mode: str,
    selection_reason: str,
    product_count: int,
    user_query: str
) -> str:
    """
    Build an introductory message explaining the AI selection.
    
    Args:
    ----
        presentation_mode: 'single', 'duo', 'trio'
        selection_reason: AI explanation
        product_count: Number of products selected
        user_query: Original user query
        
    Returns:
    -------
        Formatted message text
    """
    if presentation_mode == 'single':
        return (
            f"🎯 **AI Found Your Perfect Match!**\n\n"
            f"For your search: *{user_query}*\n\n"
            f"🤖 **AI Analysis**: {selection_reason}\n\n"
            f"Here's your best option:"
        )
    else:
        mode_text = {
            'duo': 'two great options',
            'trio': 'three competitive choices',
            'multi': f'{product_count} excellent options'
        }.get(presentation_mode, f'{product_count} options')
        
        return (
            f"🤖 **AI Found {mode_text.title()}!**\n\n"
            f"For your search: *{user_query}*\n\n"
            f"📊 **AI Analysis**: {selection_reason}\n\n"
            f"Choose the option that best fits your needs:"
        )


def format_comparison_table_text(comparison_table: Dict) -> str:
    """
    Format comparison table as readable text for Telegram.
    
    Args:
    ----
        comparison_table: Feature comparison data
        
    Returns:
    -------
        Formatted comparison text
    """
    if not comparison_table or not comparison_table.get('key_differences'):
        return "No comparison data available"
    
    text = "📊 **Feature Comparison**\n\n"
    
    key_diffs = comparison_table['key_differences']
    headers = comparison_table.get('headers', ['Feature', 'Option 1', 'Option 2', 'Option 3'])
    
    for diff in key_diffs[:5]:  # Show top 5 features
        feature = diff['feature']
        values = diff['values']
        
        text += f"**{feature}**\n"
        for i, value in enumerate(values):
            option_num = i + 1
            best_index = diff.get('highlight_best', -1)
            if i == best_index:
                text += f"  {option_num}. {value} ⭐\n"
            else:
                text += f"  {option_num}. {value}\n"
        text += "\n"
    
    return text


def get_carousel_analytics_metadata(
    presentation_mode: str,
    product_count: int,
    selection_criteria: str,
    processing_time_ms: float
) -> Dict[str, Any]:
    """
    Generate analytics metadata for carousel performance tracking.
    
    Args:
    ----
        presentation_mode: 'single', 'duo', 'trio'
        product_count: Number of products in carousel
        selection_criteria: How products were selected
        processing_time_ms: Processing time
        
    Returns:
    -------
        Analytics metadata dict
    """
    return {
        'carousel_type': 'enhanced_ai_carousel',
        'presentation_mode': presentation_mode,
        'product_count': product_count,
        'selection_criteria': selection_criteria,
        'processing_time_ms': processing_time_ms,
        'features_enabled': [
            'ai_insights',
            'comparison_table',
            'product_highlights',
            'strengths_analysis'
        ],
        'multi_card_experience': product_count > 1
    }
