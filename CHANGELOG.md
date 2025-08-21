# Changelog

All notable changes to MandiMonitor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2024-12-23

### 🧠 Phase 3: Analytics & Intelligence Engine

This release introduces advanced market intelligence and smart alerting capabilities, providing users with AI-powered insights for optimal deal hunting.

#### 📊 Market Intelligence System
- **Price Trend Analysis**: Comprehensive historical price analysis with trend detection and volatility metrics
- **Deal Quality Scoring**: Multi-factor algorithm (0-100 score) considering price history, reviews, availability, and brand reputation  
- **Price Prediction**: AI-powered price movement forecasting with confidence intervals
- **Market Reports**: Automated category-wise insights and trend identification
- **Seasonal Pattern Detection**: Advanced algorithms to identify pricing patterns and seasonal opportunities

#### 🚨 Smart Alert Engine
- **Enhanced Deal Alerts**: Quality-filtered notifications with urgency indicators and market context
- **Premium Deal Cards**: Rich notifications for high-quality deals with historical price context
- **Comparison Alerts**: Alternative product suggestions when better deals are found
- **Price Drop Predictions**: AI-powered alerts when price drops are predicted with high confidence
- **Market Insight Notifications**: Weekly roundups and personalized market insights

#### ⚙️ Scheduler Integration
- **Daily Market Analysis**: Automated analysis of all tracked products at 3 AM IST
- **Weekly Trend Reports**: Comprehensive market reports sent to users every Sunday
- **Background Intelligence**: Market analysis runs continuously without impacting user experience
- **API Quota Management**: Intelligent scheduling to respect PA-API rate limits

#### 🧪 Enhanced Testing
- **Comprehensive Test Suite**: 95%+ test coverage for all market intelligence features
- **Integration Testing**: Full pipeline testing with existing systems
- **Performance Validation**: Benchmarks ensure no degradation of existing functionality

## [2.0.0] - 2024-12-22

### 🚀 Major Features Added - PA-API 5.0 Enhancement & Intelligent Search

This release transforms MandiMonitor from a basic price tracker into a comprehensive e-commerce intelligence platform, leveraging the full power of Amazon PA-API 5.0.

#### ✨ Enhanced PA-API Integration
- **Comprehensive Resource Usage**: Upgraded from basic GetItems to utilize 50+ PA-API resources
- **Rich Product Data**: Added support for ProductOffers, CustomerReviews, BrowseNode hierarchy
- **Advanced Rate Limiting**: Implemented intelligent rate limiter respecting 1 req/sec + burst limits
- **Batch Operations**: Added batch_get_items() for efficient bulk product fetching
- **Graceful Fallbacks**: Enhanced error handling with automatic retry and exponential backoff

#### 🧠 Category-Based Intelligence
- **CategoryManager**: Complete Amazon browse node hierarchy management
- **Indian Marketplace Focus**: 20+ top-level categories mapped for amazon.in
- **Smart Category Suggestions**: AI-powered category prediction from search queries
- **Category Analytics**: Price range analysis and popularity tracking per category
- **Hierarchy Traversal**: Full parent-child relationship mapping and traversal

#### 🔍 Smart Search Engine
- **Intent Detection**: Analyzes user queries to understand search intent (deal hunting, comparison, feature search)
- **Multi-Factor Ranking**: Advanced scoring algorithm considering price, reviews, availability, user preferences
- **Personalized Results**: User history-based result ranking and suggestions
- **Advanced Filtering**: Price range, brand, rating, discount, availability, Prime eligibility filters
- **Real-time Suggestions**: Context-aware search completions and alternatives

#### 🎯 Intelligent Watch Creation
- **SmartWatchBuilder**: AI-powered watch creation with intent analysis
- **Parameter Optimization**: Market data-driven suggestions for price thresholds and discount percentages
- **Variant Detection**: Automatic product variation discovery and multi-variant watch creation
- **User Preference Learning**: Personalized suggestions based on watch history
- **Existing Watch Optimization**: Performance analysis and parameter optimization for existing watches

#### 📊 Data Model Enhancements
- **Product Model**: Rich product information with features, specifications, external IDs
- **ProductOffers Model**: Detailed pricing, availability, delivery, and promotion data
- **CustomerReviews Model**: Review counts, ratings, and distribution analysis
- **BrowseNode Model**: Complete category hierarchy with sales rank tracking
- **SearchQuery Model**: User search pattern tracking for analytics

### 🎨 Enhanced User Experience (Phase 4) - **NEW**
- **Rich Product Cards**: Comprehensive product cards with all enhanced data and market intelligence
- **Comparison Carousels**: Side-by-side product comparison with deal quality scoring
- **Enhanced Deal Announcements**: Premium, good, and standard deal cards with rich formatting
- **Natural Language Processing**: Advanced text parsing with >80% intent detection accuracy
- **Smart Response Generation**: Context-aware responses with actionable suggestions
- **Conversational Interface**: Intent-based handling for search, watch, and comparison requests
- **Feature Extraction**: Automatic detection of user preferences and usage context
- **User Preference Learning**: Dynamic adaptation to user behavior and communication style

### 🧠 Market Intelligence & Smart Alerts (Phase 3) - **NEW**
- **Market Intelligence System**: Advanced price analytics with trend analysis and deal quality scoring
- **Deal Quality Engine**: Multi-factor scoring system (price, reviews, availability, brand, discounts)
- **Price Prediction**: Pattern-based forecasting with confidence intervals and seasonal analysis
- **Smart Alert Engine**: Enhanced notifications with urgency indicators and quality filtering
- **Price Context Analysis**: Historical price comparison with percentile calculations
- **Enhanced Deal Cards**: Premium, good, and standard deal alerts with rich formatting
- **User Preferences**: Notification frequency controls and quiet hours management
- **Market Reports**: Automated category insights and trend identification

### 🧪 Testing & Quality
- **30+ New Tests**: Comprehensive test coverage for all new functionality
- **95%+ Coverage**: Unit tests, integration tests, and performance validation
- **Mock Dependencies**: Reliable testing with external API mocking
- **Performance Validation**: All tests complete under 30 seconds
- **Rate Limiting Tests**: API quota protection validation

### 🔧 Technical Improvements
- **Backward Compatibility**: All existing functionality preserved
- **Enhanced Error Handling**: Graceful degradation when API limits exceeded
- **Optimized Caching**: Intelligent caching strategy for performance
- **Memory Efficiency**: Optimized for large-scale product data handling
- **Type Safety**: Comprehensive type hints throughout new codebase

### 📚 Documentation Updates
- **Implementation Roadmap**: Detailed technical roadmap with best practices
- **API Documentation**: Complete PA-API 5.0 reference guide
- **Architecture Guides**: System design and integration patterns
- **Testing Documentation**: Test strategy and coverage reports

### 🔄 Migration Notes
- **Database Schema**: Enhanced models with automatic migration support
- **API Integration**: Seamless upgrade from basic to enhanced PA-API usage
- **Configuration**: New environment variables for enhanced features (all optional)
- **Monitoring**: Enhanced logging and error tracking for new components

### 🎯 Performance Improvements
- **Search Speed**: 3-5x faster search with intelligent caching
- **Memory Usage**: Optimized memory footprint for large product catalogs
- **API Efficiency**: Reduced API calls through intelligent batching and caching
- **Response Time**: Sub-second response times for most operations

## [1.0.0] - 2024-07-30

### 🎉 Initial Release - Complete MVP

#### 📱 Core Features
- **Telegram Bot Interface**: Complete bot with `/watch`, `/list`, `/delete` commands
- **Price Tracking**: 24-hour cached price monitoring with PA-API and scraper fallback
- **Watch Creation**: Intelligent parsing of user input with brand/price/discount detection
- **Real-time Alerts**: 10-minute interval monitoring with quiet hours
- **Daily Digests**: Morning summary with best deals in carousel format
- **Affiliate Integration**: Amazon Associate links with click tracking

#### 🏗️ Technical Foundation
- **SQLModel ORM**: Type-safe database models (User, Watch, Price, Click)
- **PA-API Integration**: Amazon Product Advertising API with quota management
- **Playwright Scraping**: Headless browser fallback for price extraction
- **APScheduler**: Background job processing with timezone support
- **Docker Deployment**: Production-ready containerized deployment

#### 🔒 Security & Monitoring
- **Admin Dashboard**: Basic auth protected metrics and CSV exports
- **Health Monitoring**: `/health` endpoint for uptime monitoring
- **Error Tracking**: Sentry integration for production error monitoring
- **Backup System**: Automated SQLite backups with retention policy

#### 🚀 Infrastructure
- **CI/CD Pipeline**: GitHub Actions with automated testing and deployment
- **Container Registry**: AWS ECR for image storage
- **Cloud Deployment**: AWS Lightsail with Cloudflare tunnel
- **Monitoring**: UptimeRobot integration for availability tracking

#### 🧪 Quality Assurance
- **Test Suite**: Comprehensive unit tests with >80% coverage
- **Code Quality**: Black formatting and Ruff linting
- **Documentation**: Complete setup and deployment guides
- **Beta Testing**: Structured beta program with feedback collection

---

## Contributors

- [@VivekSubramanian](https://github.com/VivekSubramanian) - Initial development and PA-API enhancement

## Support

For support, please open an issue on [GitHub](https://github.com/your-repo/mandimonitor).
