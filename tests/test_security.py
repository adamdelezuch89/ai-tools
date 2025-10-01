import os
import shutil
import unittest
import tempfile

from ai_tools.utils.security import (
    parse_env_file,
    mask_sensitive_values,
    get_env_values_from_project,
    hide_env_values
)


class TestEnvParsing(unittest.TestCase):
    """Testy parsowania plików .env"""
    
    def setUp(self):
        """Tworzy tymczasowy katalog dla testów."""
        self.test_dir = tempfile.mkdtemp()
        self.env_file = os.path.join(self.test_dir, '.env')
    
    def tearDown(self):
        """Usuwa tymczasowy katalog."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_parse_simple_env(self):
        """Test parsowania prostego pliku .env"""
        with open(self.env_file, 'w') as f:
            f.write("API_KEY=secret123\n")
            f.write("DATABASE_URL=postgres://user:pass@localhost/db\n")
        
        values = parse_env_file(self.env_file)
        
        self.assertIn("secret123", values)
        self.assertIn("postgres://user:pass@localhost/db", values)
        self.assertEqual(len(values), 2)
    
    def test_parse_env_with_quotes(self):
        """Test parsowania wartości w cudzysłowach"""
        with open(self.env_file, 'w') as f:
            f.write('API_KEY="secret123"\n')
            f.write("DB_PASS='password456'\n")
        
        values = parse_env_file(self.env_file)
        
        self.assertIn("secret123", values)
        self.assertIn("password456", values)
    
    def test_parse_env_with_export(self):
        """Test parsowania z prefiksem export"""
        with open(self.env_file, 'w') as f:
            f.write("export API_KEY=secret123\n")
            f.write("export DB_URL=postgres://localhost\n")
        
        values = parse_env_file(self.env_file)
        
        self.assertIn("secret123", values)
        self.assertIn("postgres://localhost", values)
    
    def test_parse_env_ignores_short_values(self):
        """Test pomijania bardzo krótkich wartości"""
        with open(self.env_file, 'w') as f:
            f.write("SHORT=ab\n")  # 2 chars - should be ignored
            f.write("API_KEY=secret123\n")  # long enough
        
        values = parse_env_file(self.env_file)
        
        self.assertNotIn("ab", values)
        self.assertIn("secret123", values)
    
    def test_parse_env_ignores_empty_values(self):
        """Test pomijania pustych wartości"""
        with open(self.env_file, 'w') as f:
            f.write("EMPTY=\n")
            f.write('EMPTY2=""\n')
            f.write("API_KEY=secret123\n")
        
        values = parse_env_file(self.env_file)
        
        self.assertIn("secret123", values)
        self.assertEqual(len(values), 1)
    
    def test_parse_nonexistent_file(self):
        """Test parsowania nieistniejącego pliku"""
        values = parse_env_file("/nonexistent/file.env")
        
        self.assertEqual(len(values), 0)


class TestMaskSensitiveValues(unittest.TestCase):
    """Testy maskowania wrażliwych wartości"""
    
    def test_mask_simple_value(self):
        """Test maskowania prostej wartości"""
        content = "API_KEY=secret123 and more text"
        sensitive = {"secret123"}
        
        result = mask_sensitive_values(content, sensitive)
        
        self.assertIn("[HIDDEN_ENV_VALUE]", result)
        self.assertNotIn("secret123", result)
    
    def test_mask_multiple_occurrences(self):
        """Test maskowania wielu wystąpień tej samej wartości"""
        content = "secret123 appears here and secret123 appears there"
        sensitive = {"secret123"}
        
        result = mask_sensitive_values(content, sensitive)
        
        self.assertEqual(result.count("[HIDDEN_ENV_VALUE]"), 2)
        self.assertNotIn("secret123", result)
    
    def test_mask_value_in_quotes(self):
        """Test maskowania wartości w cudzysłowach"""
        content = 'API_KEY="secret123"'
        sensitive = {"secret123"}
        
        result = mask_sensitive_values(content, sensitive)
        
        self.assertIn("[HIDDEN_ENV_VALUE]", result)
        self.assertNotIn("secret123", result)
    
    def test_mask_longest_first(self):
        """Test maskowania dłuższych wartości najpierw (unikanie częściowych zamian)"""
        content = "secret123456 and secret123"
        sensitive = {"secret123", "secret123456"}
        
        result = mask_sensitive_values(content, sensitive)
        
        # Obie wartości powinny być zamaskowane
        self.assertNotIn("secret123456", result)
        self.assertNotIn("secret123", result)
    
    def test_mask_case_insensitive(self):
        """Test maskowania niezależnie od wielkości liter"""
        content = "SECRET123 and secret123 and SeCrEt123"
        sensitive = {"secret123"}
        
        result = mask_sensitive_values(content, sensitive)
        
        # Wszystkie warianty powinny być zamaskowane
        self.assertEqual(result.count("[HIDDEN_ENV_VALUE]"), 3)
    
    def test_mask_empty_sensitive_set(self):
        """Test z pustym zestawem wrażliwych wartości"""
        content = "no secrets here"
        sensitive = set()
        
        result = mask_sensitive_values(content, sensitive)
        
        self.assertEqual(content, result)
    
    def test_mask_ignores_very_short_values(self):
        """Test pomijania bardzo krótkich wartości"""
        content = "ab cd ef"
        sensitive = {"ab", "cd"}  # too short
        
        result = mask_sensitive_values(content, sensitive)
        
        # Powinny pozostać nienaruszone
        self.assertEqual(content, result)


class TestGetEnvValuesFromProject(unittest.TestCase):
    """Testy pobierania wartości .env z projektu"""
    
    def setUp(self):
        """Tworzy tymczasowy katalog projektu."""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Usuwa tymczasowy katalog."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_get_values_from_single_env_file(self):
        """Test pobierania wartości z jednego pliku .env"""
        env_file = os.path.join(self.test_dir, '.env')
        with open(env_file, 'w') as f:
            f.write("API_KEY=secret123\n")
        
        values = get_env_values_from_project(self.test_dir)
        
        self.assertIn("secret123", values)
    
    def test_get_values_from_multiple_env_files(self):
        """Test pobierania wartości z wielu plików .env"""
        # Utwórz .env
        with open(os.path.join(self.test_dir, '.env'), 'w') as f:
            f.write("API_KEY=secret123\n")
        
        # Utwórz .env.local
        with open(os.path.join(self.test_dir, '.env.local'), 'w') as f:
            f.write("DB_PASSWORD=password456\n")
        
        values = get_env_values_from_project(self.test_dir)
        
        self.assertIn("secret123", values)
        self.assertIn("password456", values)
    
    def test_get_values_with_no_env_files(self):
        """Test gdy nie ma żadnych plików .env"""
        values = get_env_values_from_project(self.test_dir)
        
        self.assertEqual(len(values), 0)


class TestHideEnvValues(unittest.TestCase):
    """Testy głównej funkcji ukrywania wartości"""
    
    def setUp(self):
        """Tworzy tymczasowy katalog projektu."""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Usuwa tymczasowy katalog."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_hide_enabled(self):
        """Test ukrywania gdy jest włączone"""
        # Utwórz .env
        env_file = os.path.join(self.test_dir, '.env')
        with open(env_file, 'w') as f:
            f.write("API_KEY=secret123\n")
        
        content = "Using API_KEY secret123 to connect"
        result = hide_env_values(content, self.test_dir, hide_enabled=True)
        
        self.assertIn("[HIDDEN_ENV_VALUE]", result)
        self.assertNotIn("secret123", result)
    
    def test_hide_disabled(self):
        """Test gdy ukrywanie jest wyłączone"""
        # Utwórz .env
        env_file = os.path.join(self.test_dir, '.env')
        with open(env_file, 'w') as f:
            f.write("API_KEY=secret123\n")
        
        content = "Using API_KEY secret123 to connect"
        result = hide_env_values(content, self.test_dir, hide_enabled=False)
        
        # Nic nie powinno być zamaskowane
        self.assertEqual(content, result)
        self.assertIn("secret123", result)
    
    def test_hide_with_no_env_file(self):
        """Test gdy nie ma pliku .env"""
        content = "No secrets here"
        result = hide_env_values(content, self.test_dir, hide_enabled=True)
        
        # Nic się nie zmienia
        self.assertEqual(content, result)
    
    def test_hide_complex_scenario(self):
        """Test złożonego scenariusza z wieloma wartościami"""
        # Utwórz .env z wieloma wartościami
        env_file = os.path.join(self.test_dir, '.env')
        with open(env_file, 'w') as f:
            f.write("API_KEY=sk_test_123456789\n")
            f.write("DB_URL=postgres://user:pass@localhost:5432/db\n")
            f.write("SECRET_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\n")
        
        content = """
        const apiKey = 'sk_test_123456789';
        const dbUrl = "postgres://user:pass@localhost:5432/db";
        const token = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9;
        """
        
        result = hide_env_values(content, self.test_dir, hide_enabled=True)
        
        # Wszystkie wrażliwe wartości powinny być zamaskowane
        self.assertNotIn("sk_test_123456789", result)
        self.assertNotIn("postgres://user:pass@localhost:5432/db", result)
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", result)
        self.assertEqual(result.count("[HIDDEN_ENV_VALUE]"), 3)


if __name__ == '__main__':
    unittest.main()

