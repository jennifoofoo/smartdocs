# Contributing to SmartDocs

Thank you for your interest in contributing to SmartDocs! 🎉

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:

- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, etc.)

### Suggesting Features

Feature requests are welcome! Please open an issue describing:

- The feature you'd like to see
- Why it would be useful
- How you envision it working

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**

   - Follow existing code style
   - Add comments for complex logic
   - Update documentation if needed

4. **Test your changes**

   ```bash
   python -m pytest tests/
   ```

5. **Commit with clear messages**

   ```bash
   git commit -m "Add feature: description of what you did"
   ```

6. **Push and create a Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/smartdocs.git
cd smartdocs

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies including dev tools
pip install -r requirements.txt
pip install pytest coverage black flake8

# Run tests
pytest tests/
```

## Code Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints where appropriate
- Keep functions focused and single-purpose
- Add docstrings to functions and classes

## Project Structure

```
smartdocs/
├── app.py              # Main Chainlit app
├── src/
│   ├── core/          # Core functionality
│   ├── utilities/     # Helper functions
│   ├── datatypes/     # Data models
│   └── api/           # API endpoints
└── tests/             # Test files
```

## Testing

- Add tests for new features
- Ensure existing tests pass
- Aim for good test coverage

```bash
# Run tests
pytest tests/

# With coverage
coverage run -m pytest tests/
coverage report
```

## Questions?

Feel free to open an issue for any questions or clarifications!

---

Thank you for making SmartDocs better! 🚀
