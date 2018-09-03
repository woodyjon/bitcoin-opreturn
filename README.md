# bitcoin-opreturn

A python script to store arbitrary data on the blockchain with OP_RETURN

## what is this?

This is a python script that uses your bitcoin node to create an OP_RETURN transaction in order to add an arbitrary piece of 80 bytes of data to the bitcoin blockchain.

This script was written as part of a learning assignment for the course _COMP541 - Blockchain Programming_ of the University of Nicosia's _Master of Science in Digital Currencies_.

## how to use

1. edit .bitcoin/bitcoin.conf file to include the following:
    ```
    testnet=1 # or testnet=0 for mainnet or regtest=1 for regtest
    daemon=1
    rpcuser=aRPCUser
    rpcpassword=aRPCPassword
    ```

1. launch bitcoind

1. install the following python libs:
    ```
    $ pip install bitcoin
    $ pip install python-bitcoinlib
    $ pip install requests
    ```

1. edit the following 2 lines in the script based on your choice to use testnet or mainnet:
    ```
    bitcoinlib.SelectParams('testnet')
    linkExplorer = "https://testnet.blockchain.info/tx/"
    ```

1. run with python3 without argument and follow the instructions:
    ```
    $ python3 bitcoin-opreturn.py
    ```

