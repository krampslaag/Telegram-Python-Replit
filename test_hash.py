#!/usr/bin/env python3
"""Test script to reverse-engineer the hash calculation method"""
import hashlib
import json

# Load the blockchain
with open('data/blockchain.json', 'r') as f:
    blockchain = json.load(f)

# Test first few blocks
for i in range(min(5, len(blockchain))):
    block = blockchain[i]
    print(f"\nBlock {i}:")
    print(f"  Expected hash: {block['hash']}")
    
    # Try different hash string combinations
    # Original method
    hash_string1 = f"{block['timestamp']}{block['data']}{block['previous_hash']}{block.get('target_distance')}{block['block_height']}"
    hash1 = hashlib.sha256(hash_string1.encode()).hexdigest()
    print(f"  Method 1: {hash1} {'✓' if hash1 == block['hash'] else '✗'}")
    
    # With all fields
    hash_string2 = f"{block['timestamp']}{block['data']}{block['previous_hash']}{block.get('target_distance')}{block.get('winner_id')}{block.get('travel_distance')}{block.get('miner_address')}{block['block_height']}"
    hash2 = hashlib.sha256(hash_string2.encode()).hexdigest()
    print(f"  Method 2: {hash2} {'✓' if hash2 == block['hash'] else '✗'}")
    
    # Without block_height
    hash_string3 = f"{block['timestamp']}{block['data']}{block['previous_hash']}{block.get('target_distance')}"
    hash3 = hashlib.sha256(hash_string3.encode()).hexdigest()
    print(f"  Method 3: {hash3} {'✓' if hash3 == block['hash'] else '✗'}")
    
    # Just core fields
    hash_string4 = f"{block['timestamp']}{block['data']}{block['previous_hash']}"
    hash4 = hashlib.sha256(hash_string4.encode()).hexdigest()
    print(f"  Method 4: {hash4} {'✓' if hash4 == block['hash'] else '✗'}")