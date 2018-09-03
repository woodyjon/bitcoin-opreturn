# run with python3 without argument: $ python3 bitcoin-opreturn.py

# .bitcoin/bitcoin.conf file should include the following and bitcoind should be running:
#   testnet=1
#   daemon=1
#   rpcuser=aRPCUser
#   rpcpassword=aRPCPassword

# install the following libs:
# $ pip install bitcoin
# $ pip install python-bitcoinlib
# $ pip install requests

import bitcoin.main as vitalik # vitalik's bitcoin lib
import bitcoin as bitcoinlib # python-bitcoinlib
import bitcoin.core as bitcoinlibcore
import bitcoin.rpc as bitcoinlibrpc
import bitcoin.transaction as bitcoinlibtransaction
import binascii
import requests

nbrSatIn1BTC = 1e8

UINT_MAX = 4294967295 # use for sequence number in tx ins

# bitcoinlib.SelectParams('mainnet')
bitcoinlib.SelectParams('testnet')
# bitcoinlib.SelectParams('regtest')

# linkExplorer = "https://www.blockchain.info/tx/"
linkExplorer = "https://testnet.blockchain.info/tx/"

#
# ask user the string to record in the blockchain
#

defaultMsg = "Go Red Devils!"
msg = defaultMsg

print("\n")
inputMessage = input('Which message would you like to store in the blockchain?:\n(type enter to choose the default message: "' + defaultMsg + '")\n')
if inputMessage != "":
    msg = inputMessage

print("\n")

msgHex = binascii.hexlify(msg.encode('utf-8')).decode('utf-8')
lengthMsg = int(len(msgHex)/2) # length in bytes. 2 hex for 1 byte
lengthMsgHex = hex(lengthMsg)
lengthMsgHex = lengthMsgHex[2:] # remove 0x from the beginning of the string
if len(lengthMsgHex) == 1:
    lengthMsgHex = "0" + lengthMsgHex

# OP_RETURN message should be 80 bytes max
if lengthMsg > 80:
    print("Your message's size is greater than 80 bytes. Please start again and choose a smaller message. Size: ", lengthMsg, "bytes\n")
    quit()

#
# display the balance of the wallet
#

rpc = bitcoinlibrpc.Proxy()
print("\nWallet total balance: ", rpc.getbalance()/nbrSatIn1BTC, "BTC")
print("\n")

#
# display the list of UTXOs to the user and let him choose one.
#

listUTXOs = rpc.listunspent(1)

if len(listUTXOs) == 0:
    print("There is no UTXO available. Please create an address and send funds to it.\n")
    quit()

print("List of UTXOs:\n")

i = 1
for UTXO in listUTXOs:
    print(i, ":", UTXO['address'], "amount:", UTXO['amount']/nbrSatIn1BTC, "BTC\n")
    i+=1

indexUTXO = 0
while 1:
    inputIndexUTXO = input("Choose one UTXO (give index): ")
    if inputIndexUTXO.isdigit():
        indexUTXO = int(inputIndexUTXO)
    if indexUTXO > 0 and indexUTXO <= len(listUTXOs):
        break
    else:
        print("Index is invalid!")

print("\n")

theUTXO = listUTXOs[indexUTXO - 1]

#
# Create a new address for the change
#

changeAddress = rpc.getnewaddress()
privKeyChangeAddress = rpc.dumpprivkey(changeAddress)
pubKeyChangeAddress = vitalik.privtopub(privKeyChangeAddress)
hashPubKeyChangeAddress = vitalik.hash160(pubKeyChangeAddress)
# will result in a legacy address

#
# fee
#

# length of our transaction with 1 input and 2 outputs including one OP_RETURN is around 200 bytes + the message if the input is compressed, around 230 bytes + the message if the input is not compressed. We pessimistically choose 230 bytes and add the size of the message (80 bytes max). There is no need to be more precise here, as the fee / byte is anyway an estimation.
sizeTX = 230 + lengthMsg # bytes

# estimation of fee as sat/B
feePerByte = rpc._call("estimatesmartfee", 2) # second parameter is the number of blocks we are ok to wait. We choose 2. The result from estimatesmartfee is in BTC/kB

if 'feerate' in feePerByte: # if no error from estimatesmartfee
    feePerByte = float(feePerByte['feerate']) * nbrSatIn1BTC / 1000 # BTC/kB -> sat/B
else: # if error from estimatesmartfee, fallback to a call to blockcypher api
    urlFeeAPI = "https://api.blockcypher.com/v1/btc/test3"
    responseFeeAPI = requests.get(urlFeeAPI)
    if responseFeeAPI.ok:
        feePerByte = responseFeeAPI.json()['low_fee_per_kb'] / 1000 # sat/kB -> sat/B
    else:
        feePerByte = 5.0 # if both methods return an error, fallback to 5 sat/B

feeTX = int(feePerByte * sizeTX) # in sat

# stop if fee is too high to avoid losing too much BTC.
if feeTX > 1e6:
    print("Fee is too high. There must be an error. Please try again. Fee: ", feeTX, "sat")
    quit()

amount = theUTXO['amount'] - feeTX # the amount to send to the change address is the amount of the UTXO minus the fee.
if amount < 0:
    print("You chose a UTXO with not enough fund. Please restart and choose a UTXO with more than ", feeTX, "sat\n")
    quit()

#
# construct transaction
#

# script 1st output (OP_RETURN)
opReturnScript = "6a" # OP_RETURN
opReturnScript += lengthMsgHex # hex value of length of message
opReturnScript += msgHex # hex value of message

# lock script 2nd output (change address)
lockScriptChangeAddr = "76" # OP_DUP
lockScriptChangeAddr += "a9" # OP_HASH160
lockScriptChangeAddr += "14" # hex value of length of public key hash (decimal: 20)
lockScriptChangeAddr += hashPubKeyChangeAddress # the hash of pub key of the change address
lockScriptChangeAddr += "88" # OP_EQUALVERIFY
lockScriptChangeAddr += "ac" # OP_CHECKSIG

mainTX = {
    'ins':[
        {
            'script': '',
            'outpoint': {
                'index': theUTXO['outpoint'].n,
                'hash': bitcoinlibcore.b2lx(theUTXO['outpoint'].hash)
            },
            'sequence': UINT_MAX
        }
    ],
    'outs':[
        {
            'script': opReturnScript,
            'value': 0
        },
        {
            'script': lockScriptChangeAddr,
            'value': amount
        }
    ],
    'locktime': 0,
    'version': 1
}

rawMainTX = bitcoinlibtransaction.serialize(mainTX)

## uncomment the next 3 lines if need to debug the transaction
# deserializedRawMainTX = bitcoinlibtransaction.deserialize(rawMainTX)
# print(deserializedRawMainTX)
# print("\n")

#
# sign raw transaction
#

signedRawMainTX = rpc._call("signrawtransaction", rawMainTX) # I directly call the rpc method instead of using the lib rpc.signrawtransaction function as that function is expecting a transaction object. For the sake of the exercise, I construct the transaction manually. There are other methods to make the transaction, for instance: https://github.com/petertodd/python-bitcoinlib/blob/master/examples/spend-p2pkh-txout.py

#
# send raw transaction
#

sentRawMainTX =  rpc._call("sendrawtransaction", signedRawMainTX['hex'])
print("Transaction sent successfully. TXID: ", sentRawMainTX)
linkExplorer += sentRawMainTX
print(linkExplorer)
print("\n")