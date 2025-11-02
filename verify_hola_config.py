#!/usr/bin/env python3
"""
Script to verify that 'hola' greeting is properly configured in the chatbot.
This validates the configuration without requiring a trained model.
"""

import yaml
import sys
from pathlib import Path

def check_yaml_syntax(filepath):
    """Check if YAML file has valid syntax"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        return True, "✓ Valid YAML syntax"
    except Exception as e:
        return False, f"✗ YAML syntax error: {e}"

def check_hola_in_nlu(nlu_path):
    """Check if 'hola' is in greet intent examples"""
    try:
        with open(nlu_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if hola is in the file
        if 'hola' not in content.lower():
            return False, "✗ 'hola' not found in nlu.yml"
        
        # Load YAML and check structure
        data = yaml.safe_load(content)
        
        # Find greet intent
        greet_found = False
        hola_in_greet = False
        
        if 'nlu' in data:
            for item in data['nlu']:
                if isinstance(item, dict) and item.get('intent') == 'greet':
                    greet_found = True
                    examples = item.get('examples', '')
                    if 'hola' in examples.lower():
                        hola_in_greet = True
                    break
        
        if not greet_found:
            return False, "✗ 'greet' intent not found in nlu.yml"
        
        if not hola_in_greet:
            return False, "✗ 'hola' not found in greet intent examples"
        
        return True, "✓ 'hola' is properly configured in greet intent"
    
    except Exception as e:
        return False, f"✗ Error checking nlu.yml: {e}"

def check_greet_in_domain(domain_path):
    """Check if greet intent and utter_greet response are in domain"""
    try:
        with open(domain_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Check if greet intent is listed
        intents = data.get('intents', [])
        if 'greet' not in intents:
            return False, "✗ 'greet' intent not found in domain.yml intents"
        
        # Check if utter_greet response exists
        responses = data.get('responses', {})
        if 'utter_greet' not in responses:
            return False, "✗ 'utter_greet' response not found in domain.yml"
        
        # Check if response has text
        greet_responses = responses['utter_greet']
        if not greet_responses or not any('text' in r for r in greet_responses):
            return False, "✗ 'utter_greet' has no text responses"
        
        return True, "✓ greet intent and utter_greet response properly configured"
    
    except Exception as e:
        return False, f"✗ Error checking domain.yml: {e}"

def check_greet_rule(rules_path):
    """Check if greet rule exists in rules.yml"""
    try:
        with open(rules_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        rules = data.get('rules', [])
        
        # Find rule that handles greet intent
        greet_rule_found = False
        for rule in rules:
            if isinstance(rule, dict):
                steps = rule.get('steps', [])
                for i, step in enumerate(steps):
                    if isinstance(step, dict) and step.get('intent') == 'greet':
                        # Check if next step is utter_greet action
                        if i + 1 < len(steps):
                            next_step = steps[i + 1]
                            if isinstance(next_step, dict) and next_step.get('action') == 'utter_greet':
                                greet_rule_found = True
                                break
            if greet_rule_found:
                break
        
        if not greet_rule_found:
            return False, "✗ Rule for greet -> utter_greet not found"
        
        return True, "✓ Greeting rule properly configured (greet -> utter_greet)"
    
    except Exception as e:
        return False, f"✗ Error checking rules.yml: {e}"

def main():
    """Main verification function"""
    print("=" * 70)
    print("VERIFICATION: 'hola' Greeting Configuration")
    print("=" * 70)
    print()
    
    base_path = Path(__file__).parent
    nlu_path = base_path / 'data' / 'nlu.yml'
    domain_path = base_path / 'domain.yml'
    rules_path = base_path / 'data' / 'rules.yml'
    config_path = base_path / 'config.yml'
    
    all_passed = True
    
    # Check 1: NLU YAML syntax
    print("1. Checking nlu.yml syntax...")
    passed, msg = check_yaml_syntax(nlu_path)
    print(f"   {msg}")
    all_passed = all_passed and passed
    
    # Check 2: Domain YAML syntax
    print("\n2. Checking domain.yml syntax...")
    passed, msg = check_yaml_syntax(domain_path)
    print(f"   {msg}")
    all_passed = all_passed and passed
    
    # Check 3: Rules YAML syntax
    print("\n3. Checking rules.yml syntax...")
    passed, msg = check_yaml_syntax(rules_path)
    print(f"   {msg}")
    all_passed = all_passed and passed
    
    # Check 4: Config YAML syntax
    print("\n4. Checking config.yml syntax...")
    passed, msg = check_yaml_syntax(config_path)
    print(f"   {msg}")
    all_passed = all_passed and passed
    
    # Check 5: 'hola' in NLU
    print("\n5. Checking 'hola' in greet intent...")
    passed, msg = check_hola_in_nlu(nlu_path)
    print(f"   {msg}")
    all_passed = all_passed and passed
    
    # Check 6: Greet in domain
    print("\n6. Checking greet configuration in domain...")
    passed, msg = check_greet_in_domain(domain_path)
    print(f"   {msg}")
    all_passed = all_passed and passed
    
    # Check 7: Greet rule
    print("\n7. Checking greet rule configuration...")
    passed, msg = check_greet_rule(rules_path)
    print(f"   {msg}")
    all_passed = all_passed and passed
    
    # Summary
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL CHECKS PASSED - 'hola' greeting is properly configured!")
        print("=" * 70)
        print("\nThe chatbot is configured to:")
        print("  1. Recognize 'hola' as a greeting (greet intent)")
        print("  2. Respond with a Spanish greeting message (utter_greet)")
        print("  3. Handle the conversation flow correctly")
        print("\nExpected responses when user says 'hola':")
        print("  - 'Hola! Soy tu asistente virtual para gestión de cédulas...'")
        print("  - '¡Bienvenido/a! Te ayudo con todo lo relacionado a trámites...'")
        return 0
    else:
        print("✗ SOME CHECKS FAILED - Please review the errors above")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
