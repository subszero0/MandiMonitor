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
            'image': product.get('image_url', product.get('image', '')),
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
    if price and isinstance(price, (int, float)) and price > 0:
        if price > 100000:  # Clearly in paise (>₹1000 in paise = ₹10+)
            price_rs = price // 100
        else:
            price_rs = price  # Already in rupees
        price_text = f"₹{price_rs:,}"
    else:
        price_text = "Price updating..."
    
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
    
    # Add detailed specs for multi-card
    if total_cards > 1:
        highlights = _get_product_highlights(product, position - 1, comparison_table)
        if highlights:
            caption += "🔍 **Key Specs**:\n" + "\n".join(highlights) + "\n\n"
        
        # Add quick specs summary from comparison data
        key_diffs = comparison_table.get('key_differences', [])
        quick_specs = []
        for diff in key_diffs[:4]:  # Top 4 most important specs
            if position - 1 < len(diff['values']):
                feature = diff['feature']
                value = diff['values'][position - 1]
                if value and value != "Not specified":
                    if feature == "Refresh Rate":
                        quick_specs.append(f"⚡ {value}")
                    elif feature == "Size":
                        quick_specs.append(f"📐 {value}")
                    elif feature == "Resolution":
                        quick_specs.append(f"🖥️ {value}")
                    elif feature == "Panel Type":
                        quick_specs.append(f"🎨 {value}")
        
        if quick_specs:
            caption += "📋 " + " • ".join(quick_specs) + "\n\n"
    
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
    Build a detailed comparison summary card with technical specifications.
    
    Args:
    ----
        comparison_table: Feature comparison data
        selection_reason: AI explanation
        product_count: Number of products
        
    Returns:
    -------
        Summary card dict
    """
    caption = "🤖 **AI Detailed Comparison**\n\n"
    
    # Add selection reason
    caption += f"📋 **Why these {product_count} options?**\n{selection_reason}\n\n"
    
    # Build comprehensive specs comparison table
    key_diffs = comparison_table.get('key_differences', [])
    if key_diffs:
        caption += "📊 **Technical Specifications**:\n\n"
        
        # Add each specification row in a simple format
        gaming_specs = ['refresh_rate', 'size', 'resolution', 'panel_type', 'price']
        for diff in key_diffs:
            feature = diff['feature']
            if any(spec in feature.lower().replace(' ', '_') for spec in gaming_specs):
                values = diff['values']
                best_index = diff.get('highlight_best', -1)
                
                caption += f"**{feature}**:\n"
                for i, value in enumerate(values[:product_count]):
                    position_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
                    if best_index == i:
                        caption += f"  {position_emoji} {value} ⭐\n"
                    else:
                        caption += f"  {position_emoji} {value}\n"
                caption += "\n"
    
    # Add detailed feature analysis
    caption += "🔍 **Key Insights**:\n"
    
    # Performance insights
    refresh_rate_diff = next((d for d in key_diffs if 'refresh' in d['feature'].lower()), None)
    if refresh_rate_diff:
        rates = [v for v in refresh_rate_diff['values'] if v and 'hz' in str(v).lower()]
        if rates:
            max_rate = max([int(''.join(filter(str.isdigit, str(r)))) for r in rates if any(c.isdigit() for c in str(r))])
            caption += f"• **Gaming Performance**: Up to {max_rate}Hz for smooth gameplay\n"
    
    # Display insights
    size_diff = next((d for d in key_diffs if 'size' in d['feature'].lower()), None)
    resolution_diff = next((d for d in key_diffs if 'resolution' in d['feature'].lower()), None)
    if size_diff and resolution_diff:
        sizes = [v for v in size_diff['values'] if v and '"' in str(v)]
        resolutions = [v for v in resolution_diff['values'] if v]
        if sizes and resolutions:
            caption += f"• **Display Options**: {len(set(sizes))} size variants, {len(set(resolutions))} resolution options\n"
    
    # Price range analysis
    price_diff = next((d for d in key_diffs if 'price' in d['feature'].lower()), None)
    if price_diff:
        prices = []
        for v in price_diff['values']:
            if v and '₹' in str(v):
                try:
                    price_num = int(''.join(filter(str.isdigit, str(v))))
                    prices.append(price_num)
                except:
                    pass
        if len(prices) >= 2:
            min_price = min(prices)
            max_price = max(prices)
            savings = max_price - min_price
            caption += f"• **Budget Range**: ₹{min_price:,} - ₹{max_price:,} (₹{savings:,} difference)\n"
    
    # Panel technology insights
    panel_diff = next((d for d in key_diffs if 'panel' in d['feature'].lower()), None)
    if panel_diff:
        panels = set([v for v in panel_diff['values'] if v and v != 'Not specified'])
        if panels:
            caption += f"• **Panel Tech**: {', '.join(panels)} available\n"
    
    caption += "\n"
    
    # Add trade-offs analysis
    trade_offs = comparison_table.get('trade_offs', [])
    if trade_offs:
        caption += "⚖️ **Trade-offs to Consider**:\n"
        for i, trade_off in enumerate(trade_offs[:3], 1):
            caption += f"{i}. {trade_off}\n"
        caption += "\n"
    
    # Product-specific recommendations
    caption += "💡 **Specific Recommendations**:\n\n"
    
    # Analyze each option specifically
    for i in range(min(product_count, 3)):
        option_num = i + 1
        position_emoji = ["🥇", "🥈", "🥉"][i]
        
        # Get product details from comparison table
        price_value = "Unknown"
        size_value = "Unknown"
        resolution_value = "Unknown"
        refresh_value = "Unknown"
        
        for diff in key_diffs:
            if i < len(diff['values']):
                if 'price' in diff['feature'].lower():
                    price_value = diff['values'][i]
                elif 'size' in diff['feature'].lower():
                    size_value = diff['values'][i]
                elif 'resolution' in diff['feature'].lower():
                    resolution_value = diff['values'][i]
                elif 'refresh' in diff['feature'].lower():
                    refresh_value = diff['values'][i]
        
        # Generate specific recommendation for this option
        caption += f"**{position_emoji} Option {option_num}**:\n"
        
        # Price positioning
        if "₹" in str(price_value):
            try:
                price_num = int(''.join(filter(str.isdigit, str(price_value))))
                if price_num < 10000:
                    price_tier = "Budget-friendly"
                elif price_num < 15000:
                    price_tier = "Mid-range value"
                elif price_num < 20000:
                    price_tier = "Premium choice"
                else:
                    price_tier = "High-end option"
            except:
                price_tier = "Competitive pricing"
        else:
            price_tier = "Good value"
        
        # Gaming performance
        gaming_perf = "Standard gaming"
        if "180" in str(refresh_value) or "200" in str(refresh_value):
            gaming_perf = "Excellent for competitive gaming"
        elif "144" in str(refresh_value) or "165" in str(refresh_value):
            gaming_perf = "Great for gaming"
        elif "120" in str(refresh_value):
            gaming_perf = "Good for casual gaming"
        
        # Screen size context
        size_context = "Standard setup"
        if "27" in str(size_value) or "32" in str(size_value):
            size_context = "Great for immersive gaming"
        elif "24" in str(size_value):
            size_context = "Perfect for competitive gaming"
        
        # Resolution benefit
        res_benefit = "Clear visuals"
        if "1440p" in str(resolution_value) or "QHD" in str(resolution_value):
            res_benefit = "Sharp, detailed visuals"
        elif "4K" in str(resolution_value):
            res_benefit = "Ultra-sharp, future-proof"
        elif "1080p" in str(resolution_value):
            res_benefit = "Smooth performance"
        
        caption += f"• **{price_tier}** at {price_value}\n"
        caption += f"• **{gaming_perf}** with {refresh_value}\n"
        caption += f"• **{size_context}** with {size_value} screen\n"
        caption += f"• **{res_benefit}** at {resolution_value}\n"
        
        # Who should choose this option
        try:
            price_num = int(''.join(filter(str.isdigit, str(price_value))))
            if price_num < 10000:
                target_user = "**Best for**: Budget gamers, students, first-time buyers"
            elif price_num < 15000:
                target_user = "**Best for**: Serious gamers wanting good value"
            elif "1440p" in str(resolution_value):
                target_user = "**Best for**: Enthusiasts wanting premium experience"
            else:
                target_user = "**Best for**: Competitive gamers, content creators"
        except:
            if "1440p" in str(resolution_value) or "QHD" in str(resolution_value):
                target_user = "**Best for**: Enthusiasts wanting premium experience"
            elif "180" in str(refresh_value) or "200" in str(refresh_value):
                target_user = "**Best for**: Competitive gamers, esports players"
            else:
                target_user = "**Best for**: General gaming, productivity"
        
        caption += f"• {target_user}\n\n"
    
    # Overall recommendation summary
    caption += "🎯 **Quick Decision Guide**:\n"
    
    # Find the cheapest, highest resolution, and largest screen
    cheapest_idx = -1
    best_resolution_idx = -1
    largest_screen_idx = -1
    
    min_price = float('inf')
    best_res_score = 0  # 4K=3, 1440p=2, 1080p=1
    max_size = 0
    
    for i, diff in enumerate(key_diffs):
        if 'price' in diff['feature'].lower():
            for j, value in enumerate(diff['values'][:product_count]):
                try:
                    price_num = int(''.join(filter(str.isdigit, str(value))))
                    if price_num < min_price:
                        min_price = price_num
                        cheapest_idx = j
                except:
                    pass
        elif 'resolution' in diff['feature'].lower():
            for j, value in enumerate(diff['values'][:product_count]):
                res_score = 0
                if "4K" in str(value): res_score = 3
                elif "1440p" in str(value): res_score = 2
                elif "1080p" in str(value): res_score = 1
                if res_score > best_res_score:
                    best_res_score = res_score
                    best_resolution_idx = j
        elif 'size' in diff['feature'].lower():
            for j, value in enumerate(diff['values'][:product_count]):
                try:
                    size_num = float(''.join(c for c in str(value) if c.isdigit() or c == '.'))
                    if size_num > max_size:
                        max_size = size_num
                        largest_screen_idx = j
                except:
                    pass
    
    if cheapest_idx >= 0:
        caption += f"• **Tightest Budget**: Go with Option {cheapest_idx + 1}\n"
    if best_resolution_idx >= 0 and best_resolution_idx != cheapest_idx:
        caption += f"• **Best Visual Quality**: Choose Option {best_resolution_idx + 1}\n"
    if largest_screen_idx >= 0 and largest_screen_idx not in [cheapest_idx, best_resolution_idx]:
        caption += f"• **Maximum Immersion**: Pick Option {largest_screen_idx + 1}\n"
    
    # Add value-for-money analysis
    caption += "\n💰 **Value Analysis**:\n"
    
    # Calculate price per inch and price per Hz for value comparison
    for i in range(min(product_count, 3)):
        price_value = "Unknown"
        size_value = "Unknown"
        refresh_value = "Unknown"
        
        for diff in key_diffs:
            if i < len(diff['values']):
                if 'price' in diff['feature'].lower():
                    price_value = diff['values'][i]
                elif 'size' in diff['feature'].lower():
                    size_value = diff['values'][i]
                elif 'refresh' in diff['feature'].lower():
                    refresh_value = diff['values'][i]
        
        try:
            price_num = int(''.join(filter(str.isdigit, str(price_value))))
            size_num = float(''.join(c for c in str(size_value) if c.isdigit() or c == '.'))
            refresh_num = int(''.join(filter(str.isdigit, str(refresh_value))))
            
            if size_num > 0:
                price_per_inch = price_num / size_num
                caption += f"• **Option {i+1}**: ₹{price_per_inch:.0f} per inch"
                
                if refresh_num > 60:
                    hz_premium = (refresh_num - 60) / 60
                    caption += f" • {hz_premium:.0%} refresh premium\n"
                else:
                    caption += " • Standard refresh rate\n"
        except:
            caption += f"• **Option {i+1}**: Good overall value\n"
    
    # Gaming use case recommendations
    caption += "\n🎮 **Gaming Use Cases**:\n"
    caption += "• **Competitive FPS**: Prioritize highest refresh rate (144Hz+)\n"
    caption += "• **RPG/Single Player**: Focus on larger screen + better resolution\n"
    caption += "• **Streaming/Content**: Consider dual monitor setup potential\n"
    caption += "• **Professional Work**: Larger screen size trumps refresh rate\n"
    
    caption += "\n👆 **Tap any product above to create your watch!**"
    
    return {
        'caption': caption,
        'keyboard': None,  # No button for summary card
        'image': '',
        'asin': '',
        'type': 'summary_card'
    }


def _get_product_highlights(product: Dict, product_index: int, comparison_table: Dict) -> List[str]:
    """Get detailed technical highlights for a product in comparison context."""
    highlights = []
    
    # Get key differences and highlight where this product stands out
    key_diffs = comparison_table.get('key_differences', [])
    
    # Prioritize gaming-relevant features
    gaming_priority = ['refresh_rate', 'resolution', 'size', 'panel_type', 'price']
    
    # Sort features by gaming relevance
    sorted_diffs = sorted(key_diffs[:6], key=lambda x: 
                         gaming_priority.index(x['feature'].lower().replace(' ', '_')) 
                         if x['feature'].lower().replace(' ', '_') in gaming_priority else 999)
    
    for diff in sorted_diffs:
        feature = diff['feature']
        values = diff['values']
        
        if product_index < len(values):
            value = values[product_index]
            
            if value and value != "Not specified":
                # Add gaming context to highlights
                best_index = diff.get('highlight_best', -1)
                is_best = best_index == product_index
                
                if feature.lower() == "refresh rate":
                    if is_best:
                        highlights.append(f"• **{value}** - Best for smooth gaming ⭐")
                    else:
                        gaming_quality = "Excellent" if "180" in value or "240" in value else \
                                       "Great" if "144" in value or "165" in value else \
                                       "Good" if "120" in value else "Standard"
                        highlights.append(f"• **{value}** - {gaming_quality} for gaming")
                        
                elif feature.lower() == "resolution":
                    if is_best:
                        highlights.append(f"• **{value}** - Best visual clarity ⭐")
                    else:
                        quality_desc = "Ultra-sharp" if "4K" in value else \
                                     "Sharp" if "1440p" in value else "Clear"
                        highlights.append(f"• **{value}** - {quality_desc} visuals")
                        
                elif feature.lower() == "size":
                    if is_best:
                        highlights.append(f"• **{value}** screen - Optimal size ⭐")
                    else:
                        size_desc = "Large" if "27" in value or "32" in value else \
                                  "Compact" if "24" in value else "Standard"
                        highlights.append(f"• **{value}** screen - {size_desc} gaming setup")
                        
                elif feature.lower() == "panel type":
                    if is_best:
                        highlights.append(f"• **{value}** panel - Premium display ⭐")
                    else:
                        panel_desc = "Premium colors" if "IPS" in value else \
                                   "High contrast" if "VA" in value else \
                                   "Fast response" if "TN" in value else "Quality"
                        highlights.append(f"• **{value}** panel - {panel_desc}")
                        
                elif feature.lower() == "price":
                    if is_best:
                        highlights.append(f"• **{value}** - Best value ⭐")
                    else:
                        highlights.append(f"• **{value}** - Competitive pricing")
                else:
                    # Generic highlight for other features
                    if is_best:
                        highlights.append(f"• **{feature}**: {value} ⭐")
                    else:
                        highlights.append(f"• **{feature}**: {value}")
    
    return highlights[:4]  # Limit to top 4 highlights


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
