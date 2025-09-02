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
    Build optimized comparison summary card with smart formatting.
    Phase R4.3: Enhanced for better readability and performance.
    
    Args:
    ----
        comparison_table: Feature comparison data
        selection_reason: AI explanation
        product_count: Number of products
        
    Returns:
    -------
        Optimized summary card dict
    """
    caption = "🤖 **AI Smart Comparison**\n\n"
    
    # Add selection reason
    caption += f"📋 **Why these {product_count} options?**\n{selection_reason}\n\n"
    
    # Build optimized specs comparison table - R4.3: Priority features first
    key_diffs = comparison_table.get('key_differences', [])
    priority_features = comparison_table.get('priority_features', [])
    
    if key_diffs:
        caption += "📊 **Key Specifications**:\n\n"
        
        # R4.3: Show priority features first, limit to top 4 for readability
        shown_features = 0
        
        # First, show priority features
        for priority_feature in priority_features[:3]:  # Top 3 priority features
            for diff in key_diffs:
                feature = diff['feature']
                if (priority_feature in feature.lower().replace(' ', '_') or 
                    feature.lower().replace(' ', '_') == priority_feature):
                    
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
                    shown_features += 1
                    break
            
            if shown_features >= 4:  # Limit to prevent overcrowding
                break
        
        # Add remaining important features if we haven't hit the limit
        if shown_features < 4:
            remaining_specs = ['price', 'size', 'resolution']  # Always important
            for spec in remaining_specs:
                if shown_features >= 4:
                    break
                    
                for diff in key_diffs:
                    feature = diff['feature']
                    if (spec in feature.lower().replace(' ', '_') and 
                        not any(pf in feature.lower().replace(' ', '_') for pf in priority_features[:3])):
                        
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
                        shown_features += 1
                        break
    
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
    """Get detailed technical highlights for a product with enhanced differentiation."""
    highlights = []

    # Extract detailed product features for enhanced messaging
    product_features = product.get('features', {})

    # Get comprehensive scoring breakdown if available
    scoring_breakdown = product.get('scoring_breakdown', {})
    technical_score = scoring_breakdown.get('technical_score', 0)
    value_score = scoring_breakdown.get('value_score', 0)
    budget_score = scoring_breakdown.get('budget_score', 0)

    # Price analysis with tier positioning
    price = product.get('price', 0)
    if price and isinstance(price, (int, float)) and price > 0:
        if price > 100000:  # Convert paise to rupees
            price_rs = price // 100
        else:
            price_rs = int(price)

        # Price positioning with context
        if price_rs < 20000:
            price_tier = "Budget-friendly"
            highlights.append(f"• **₹{price_rs:,}** - {price_tier}, great for entry-level gaming")
        elif price_rs < 35000:
            price_tier = "Mid-range value"
            highlights.append(f"• **₹{price_rs:,}** - {price_tier}, sweet spot for most gamers")
        elif price_rs < 50000:
            price_tier = "Premium"
            highlights.append(f"• **₹{price_rs:,}** - {price_tier}, high-end gaming performance")
        else:
            price_tier = "High-end flagship"
            highlights.append(f"• **₹{price_rs:,}** - {price_tier}, ultimate gaming experience")

    # Enhanced refresh rate analysis with gaming context
    refresh_rate = product_features.get('refresh_rate', 0)
    if refresh_rate:
        if refresh_rate >= 240:
            highlights.append(f"• **{refresh_rate}Hz** ⚡ Ultra-smooth for competitive esports")
        elif refresh_rate >= 165:
            highlights.append(f"• **{refresh_rate}Hz** ⚡ Excellent for fast-paced FPS games")
        elif refresh_rate >= 144:
            highlights.append(f"• **{refresh_rate}Hz** ⚡ Great for most modern games")
        else:
            highlights.append(f"• **{refresh_rate}Hz** - Good for casual gaming & work")

    # Enhanced response time analysis
    response_time = product_features.get('response_time', 0)
    if response_time:
        if response_time <= 1:
            highlights.append(f"• **{response_time}ms** 🏆 Virtually no motion blur in fast action")
        elif response_time <= 4:
            highlights.append(f"• **{response_time}ms** ✨ Very sharp motion, minimal ghosting")
        else:
            highlights.append(f"• **{response_time}ms** - Decent for general gaming use")

    # Enhanced resolution analysis with use case context
    resolution = product_features.get('resolution', '').upper()
    if resolution:
        if '4K' in resolution or 'UHD' in resolution:
            highlights.append(f"• **{resolution}** 🎯 Ultra-high definition for professional content creation")
        elif '1440P' in resolution or 'QHD' in resolution:
            highlights.append(f"• **{resolution}** 🎯 Sharp, detailed graphics for gaming & media")
        elif '1080P' in resolution or 'FHD' in resolution:
            highlights.append(f"• **{resolution}** - Clear visuals, excellent performance on any GPU")

    # Enhanced panel type analysis with specific benefits
    panel_type = product_features.get('panel_type', '').upper()
    if panel_type:
        if 'IPS' in panel_type:
            highlights.append(f"• **{panel_type} Panel** 🎨 Best color accuracy & wide viewing angles")
        elif 'VA' in panel_type:
            highlights.append(f"• **{panel_type} Panel** 🌙 Excellent contrast & deep blacks")
        elif 'OLED' in panel_type or 'AMOLED' in panel_type:
            highlights.append(f"• **{panel_type} Panel** 💫 Perfect blacks & vibrant HDR colors")
        else:
            highlights.append(f"• **{panel_type} Panel** - Reliable display technology")

    # HDR support with specific benefits
    hdr = product_features.get('hdr_support', '').upper()
    if hdr and 'HDR' in hdr:
        highlights.append(f"• **{hdr}** 🌈 Enhanced contrast, brighter highlights & vivid colors")

    # Color accuracy for creative professionals
    color_acc = product_features.get('color_accuracy', 0)
    if color_acc and color_acc > 0:
        if color_acc >= 95:
            highlights.append(f"• **{color_acc}% sRGB** 🎨 Professional color accuracy for content creation")
        elif color_acc >= 85:
            highlights.append(f"• **{color_acc}% sRGB** - Good color reproduction for casual creators")

    # Brightness with room context
    brightness = product_features.get('brightness', 0)
    if brightness and brightness > 0:
        if brightness >= 400:
            highlights.append(f"• **{brightness} nits** ☀️ Perfect for bright rooms & outdoor visibility")
        elif brightness >= 300:
            highlights.append(f"• **{brightness} nits** - Good brightness for most indoor environments")

    # Value assessment based on comprehensive scoring
    if value_score >= 0.8:
        highlights.append("• **💰 Excellent Value** - Outstanding performance per rupee spent")
    elif value_score >= 0.6:
        highlights.append("• **👍 Good Value** - Solid performance relative to price")
    elif value_score <= 0.4:
        highlights.append("• **⚠️ Premium Investment** - Consider if advanced features are needed")

    # Technical excellence indicators
    excellence_indicators = []
    if refresh_rate and refresh_rate >= 144:
        excellence_indicators.append("high refresh rate")
    if response_time and response_time <= 4:
        excellence_indicators.append("fast response time")
    if 'IPS' in panel_type or 'OLED' in panel_type:
        excellence_indicators.append("premium panel")
    if color_acc and color_acc >= 90:
        excellence_indicators.append("professional color accuracy")

    if len(excellence_indicators) >= 2:
        highlights.append(f"• **🏆 Technical Excellence** - {', '.join(excellence_indicators[:2])} & more")

    # Limit to top 5 highlights for optimal readability
    return highlights[:5]


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
