from web3 import Web3
import json
import time

# ------------------------- CONFIGURATION -------------------------
RPC_URL = "<>"  # BSC Mainnet or Testnet RPC
PRIVATE_KEY = "<>"  # Private Key of the deployer
PUBLIC_ADDRESS = "<>"  # Deployer's address

PANCAKESWAP_ROUTER_V2 = "<>"  # PancakeSwap V2 Router (Mainnet)
PANCAKESWAP_FACTORY_V2 = "<>"  # Factory
WBNB_ADDRESS = "<>"  # Wrapped BNB

TOKEN_NAME = "Broccoli"
TOKEN_SYMBOL = "Broccoli"
TOKEN_SUPPLY = 1_000_000_000  # 1 Billion Tokens
LIQUIDITY_PERCENTAGE = 0.99  # 90% of token supply
BNB_AMOUNT = Web3.to_wei(5, 'ether')  # 5 BNB

# Connect to Web3 Provider
web3 = Web3(Web3.HTTPProvider(RPC_URL))
assert web3.is_connected(), "Failed to connect to BSC"

# Get Nonce
def get_nonce():
    return web3.eth.get_transaction_count(PUBLIC_ADDRESS)

def deploy_contract():
    with open("ercabi.json") as abi_file:
        contract_abi = json.load(abi_file)

    with open("ercbytecode.json") as bytecode_file:
        contract_bytecode = bytecode_file.read().strip()

    print("Deploying Token Contract...")
    TokenContract = web3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)
    
    transaction = TokenContract.constructor(TOKEN_NAME, TOKEN_SYMBOL, TOKEN_SUPPLY).build_transaction({
        "from": PUBLIC_ADDRESS,
        "gas": 3000000,
        "gasPrice": web3.to_wei('1', 'gwei'),
        "nonce": get_nonce()
    })
    
    try:
        signed_tx = web3.eth.account.sign_transaction(transaction, PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"Transaction Sent: {tx_hash.hex()}")
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Token Contract Deployed at: {receipt.contractAddress}")
        return receipt.contractAddress
    except Exception as e:
        print(f"Error deploying contract: {e}")
        return None

def approve_router(token_address):
    with open("ercabi.json") as abi_file:
        token_abi = json.load(abi_file)
    
    token_contract = web3.eth.contract(address=token_address, abi=token_abi)
    amount_to_approve = int(TOKEN_SUPPLY * LIQUIDITY_PERCENTAGE)
    
    print("Approving Router...")
    approve_tx = token_contract.functions.approve(PANCAKESWAP_ROUTER_V2, amount_to_approve).build_transaction({
        "from": PUBLIC_ADDRESS,
        "gas": 100000,
        "gasPrice": web3.to_wei('2', 'gwei'),
        "nonce": get_nonce()
    })
    
    try:
        signed_tx = web3.eth.account.sign_transaction(approve_tx, PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"Transaction Sent: {tx_hash.hex()}")
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Router Approved to spend tokens: {receipt.transactionHash.hex()}")
        # ✅ Wait for Approval to be Registered on BSC
        print("Waiting for approval to be confirmed...")

    except Exception as e:
        print(f"Error approving router: {e}")

def check_approval(token_address, spender, amount):
    with open("ercabi.json") as abi_file:
        token_abi = json.load(abi_file)
    
    token_contract = web3.eth.contract(address=token_address, abi=token_abi)
    allowance = token_contract.functions.allowance(PUBLIC_ADDRESS, spender).call()
    return allowance >= amount

def add_liquidity(token_address):
    with open("router.json") as abi_file:
        router_abi = json.load(abi_file)
    
    router_contract = web3.eth.contract(address=PANCAKESWAP_ROUTER_V2, abi=router_abi)
    tokens_to_add = int(TOKEN_SUPPLY * LIQUIDITY_PERCENTAGE)
    
    slippage_tolerance = 0.99  # Allow 1% slippage
    deadline = int(time.time()) + 1800  # 30 minutes deadline
    
    # Check if approval is sufficient before adding liquidity
    if not check_approval(token_address, PANCAKESWAP_ROUTER_V2, tokens_to_add):
        print("Error: Router does not have sufficient approval for the token.")
        return
    
    print("Adding Liquidity...")
    try:
        liquidity_tx = router_contract.functions.addLiquidityETH(
            token_address,
            tokens_to_add,
            int(tokens_to_add * slippage_tolerance),  # Min Tokens with slippage tolerance
            int(BNB_AMOUNT * slippage_tolerance),  # Min BNB with slippage tolerance
            PUBLIC_ADDRESS,
            deadline
        ).build_transaction({
            "from": PUBLIC_ADDRESS,
            "value": BNB_AMOUNT,
            "gas": 4000000,  # Increased gas to avoid underestimation
            "gasPrice": web3.to_wei('2', 'gwei'),  # Slightly higher gas price
            "nonce": get_nonce()
        })
        
        signed_tx = web3.eth.account.sign_transaction(liquidity_tx, PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"Transaction Sent: {tx_hash.hex()}")
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Liquidity Added: {receipt.transactionHash.hex()}")
    except Exception as e:
        print(f"Error adding liquidity: {e}")
        if hasattr(e, 'args') and len(e.args) > 0:
            print(f"Error details: {e.args[0]}")

def get_pair_address(token_address):
    with open("factoryabi.json") as abi_file:
        factory_abi = json.load(abi_file)
    
    factory_contract = web3.eth.contract(address=PANCAKESWAP_FACTORY_V2, abi=factory_abi)
    try:
        pair_address = factory_contract.functions.getPair(token_address, WBNB_ADDRESS).call()
        print(f"PancakeSwap Pair Address: {pair_address}")
    except Exception as e:
        print(f"Error fetching pair address: {e}")

# Main Execution
if __name__ == "__main__":
    deployed_token = deploy_contract()
    if deployed_token:
        approve_router(deployed_token)
        add_liquidity(deployed_token)
        get_pair_address(deployed_token)
