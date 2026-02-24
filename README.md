# StackSense

AI Economic Intelligence Layer. StackSense goes beyond observability—it is an active optimization engine that automatically reduces AI spend, routes requests intelligently, and acts as a CFO for your AI infrastructure.

## Features

- 🧠 **Smart Model Routing**: Dynamically route prompts to the most cost-effective model based on task complexity.
- ♻️ **Token Waste Detection**: Identify inefficient prompt structures and recurrent context to recover wasted tokens.
- 📉 **Automatic Cost Downgrading**: Set budget circuit breakers that auto-downgrade model tiers when approaching limits.
- 🎯 **Prompt Efficiency Scoring**: Score prompts based on token ratio, retry rates, and cost per successful outcome.
- 💸 **AI Unit Economics**: Track AI cost per user, feature, or workflow to accurately measure margin impact.
- ⚖️ **Cross-Vendor Arbitrage**: Automatically shift traffic between providers based on real-time pricing and latency gaps.
- 🔍 **Automatic Tracking**: Monitor API calls across OpenAI, Anthropic, ElevenLabs, Pinecone, and more without code changes.
- 📊 **Performance Metrics**: Latency, error rates, and hallucination cost detection.

## Quick Start

### Installation

```bash
pip install stacksense
```

### Basic Usage

```python
from stacksense import StackSense
import openai

# Initialize StackSense
ss = StackSense(api_key="your_key")

# Monitor your OpenAI client
client = ss.monitor(openai.OpenAI())

# All API calls are automatically tracked
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)

# Get metrics
metrics = ss.get_metrics(timeframe="24h")
print(f"Total cost: ${metrics['total_cost']}")
```

## Database Support

StackSense includes built-in database persistence:

```bash
# SQLite (default - no setup required)
# Data stored in ./stacksense.db

# PostgreSQL (production)
pip install stacksense[postgresql]  # or stacksense[postgres]
export STACKSENSE_DB_URL="postgresql://user:pass@host:5432/stacksense"
```

See [docs/DATABASE_GUIDE.md](docs/DATABASE_GUIDE.md) for detailed database configuration.

## Docker Deployment

### Quick Start with Docker Compose

```bash
# Start PostgreSQL and services
docker-compose up -d

# Your application will connect automatically
```

### Custom Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install StackSense with PostgreSQL support
RUN pip install stacksense[postgres]

# Copy and install your application
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Set environment variables
ENV STACKSENSE_ENABLE_DB=true
ENV STACKSENSE_DB_URL=postgresql://user:pass@postgres:5432/stacksense

CMD ["python", "app.py"]
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete deployment guide.

## Configuration

### Environment Variables

```bash
# API Configuration
STACKSENSE_API_KEY=your_api_key
STACKSENSE_PROJECT_ID=your_project_id

# Database Configuration
STACKSENSE_ENABLE_DB=true
STACKSENSE_DB_URL=sqlite:///stacksense.db  # or PostgreSQL URL
STACKSENSE_DB_ECHO=false

# Environment
STACKSENSE_ENVIRONMENT=production
STACKSENSE_DEBUG=false
```

## Documentation

- [docs/QUICKSTART.md](docs/QUICKSTART.md) - Quick start guide
- [docs/DATABASE_GUIDE.md](docs/DATABASE_GUIDE.md) - Database setup and usage
- [docs/DATABASE_ARCHITECTURE.md](docs/DATABASE_ARCHITECTURE.md) - Database architecture details
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Production deployment instructions
- [docs/USER_JOURNEY.md](docs/USER_JOURNEY.md) - Complete user journey and backend flow
- [API Documentation](https://stacksense.readthedocs.io) - Full API reference

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/Abdulkvng/stacksense.git
cd stacksense

# Install development dependencies
make dev-install
# or
pip install -e ".[dev]"
```

### Running Tests

```bash
make test
# or
pytest tests/
```

### Code Quality

```bash
# Format code
make format

# Run linters
make lint
```

## Publishing to PyPI

### Automated (Recommended)

1. Update version in `pyproject.toml`
2. Create a GitHub Release tag (e.g., `v0.1.0`)
3. GitHub Actions will automatically publish to PyPI

### Manual

```bash
# Build package
make build

# Publish to PyPI
make publish
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed publishing instructions.

## CI/CD

The repository includes GitHub Actions workflows:

- **CI**: Runs tests, linters, and type checkers on push/PR
- **Publish**: Automatically publishes to PyPI on release

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

- **Issues**: [GitHub Issues](https://github.com/Abdulkvng/stacksense/issues)
- **Documentation**: [Read the Docs](https://stacksense.readthedocs.io)

## Author

Abdulrahman Sadiq - abdulkvng@gmail.com

