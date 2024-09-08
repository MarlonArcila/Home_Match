import os
import environ
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from django.contrib.auth import authenticate, login as django_login, authenticate
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.generic.edit import UpdateView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from datetime import datetime, timedelta
from io import BytesIO
from django.core.exceptions import ObjectDoesNotExist
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.views.generic.list import ListView
from django.db import IntegrityError
from django.contrib.auth.models import User
from rest_framework.response import Response
from .forms import CustomUser
from django.core.exceptions import ValidationError
from .models import Inmueble, Puja, InmuebleFoto, ArrendatarioCriterios
from django.utils import timezone
import json
from django.db.models import Q
from django.conf import settings
import requests
from decimal import Decimal
from web3 import Web3

# Initialize logger
logger = logging.getLogger(__name__)

# Property creation logic
@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Only authenticated users can create properties
def crear_inmueble(request):
    """
    Allows landlords to create a new property, including photos (up to 10).
    """
    # Check if the user is a landlord
    if request.user.user_type != 'arrendador':
        return Response({"error": "Only landlords can create properties."}, status=403)

    data = request.data
    # Create the property using the provided data
    nuevo_inmueble = Inmueble.objects.create(
        nombre=data['nombre'],
        direccion=data['direccion'],
        metros_cuadrados=data['metros_cuadrados'],
        habitaciones=data['habitaciones'],
        baños=data['baños'],
        estado_conservacion=data['estado_conservacion'],
        amenidades=data['amenidades'],
        fecha_publicacion=data['fecha_publicacion'],
    )

    # Verify that no more than 10 images are uploaded
    imagenes = request.FILES.getlist('imagenes')
    if len(imagenes) > 10:
        return Response({"error": "Cannot upload more than 10 images"}, status=400)

    # Upload images if everything is correct
    for imagen in imagenes:
        InmuebleFoto.objects.create(inmueble=nuevo_inmueble, imagen=imagen)

    return JsonResponse({"message": "Property created successfully and photos uploaded."})

# Matching and property ranking logic
@api_view(['POST'])
def calcular_score(request):
    """
    Calculates the matching score between a tenant and a property based on selected criteria.
    """
    arrendatario_id = request.data.get('arrendatario_id')
    inmueble_id = request.data.get('inmueble_id')

    try:
        # Get the selected scores for the tenant
        criterios = ArrendatarioCriterios.objects.get(arrendatario_id=arrendatario_id, inmueble_id=inmueble_id)

        # Define weights for each criterion on a scale of 1 to 5
        pesos = {
            'metros_cuadrados': criterios.metros_cuadrados,
            'habitaciones': criterios.habitaciones,
            'baños': criterios.baños,
            'estado_conservacion': criterios.estado_conservacion,
            'amenidades': criterios.amenidades,
            'riesgos_de_avenida': criterios.riesgos_de_avenida,
            'atractivos_turisticos': criterios.atractivos_turisticos,
            'espacios_publicos': criterios.espacios_publicos,
            'paradas_transporte_publico': criterios.paradas_transporte_publico,
            'establecimientos_comerciales': criterios.establecimientos_comerciales,
            'establecimientos_educativos': criterios.establecimientos_educativos,
        }

        # Calculate the weighted average (multiply each criterion by its weight)
        total_puntuacion = 0
        total_pesos = 0
        for key, value in pesos.items():
            total_puntuacion += value * 5  # 5 is the maximum Likert scale value
            total_pesos += 5  # All weights sum to 5 (customizable)

        # Calculate the score as a weighted average
        score = total_puntuacion / total_pesos

        return Response({'score': score})

    except ArrendatarioCriterios.DoesNotExist:
        return Response({"error": "No criteria found for this tenant and property."}, status=404)

# Searching and ranking properties based on matches
@api_view(['GET'])
def buscar_inmuebles_rankeados(request):
    """
    Searches for properties and ranks them based on the matching score using tenant criteria.
    """
    arrendatario_id = request.query_params.get('arrendatario_id')

    # Get all properties and calculate the matching score for each
    inmuebles = Inmueble.objects.all()
    resultados = []

    for inmueble in inmuebles:
        # Calculate the score for each property
        criterios = ArrendatarioCriterios.objects.get(arrendatario_id=arrendatario_id, inmueble_id=inmueble.id)
        pesos = {
            'metros_cuadrados': criterios.metros_cuadrados,
            'habitaciones': criterios.habitaciones,
            'baños': criterios.baños,
            'estado_conservacion': criterios.estado_conservacion,
            'amenidades': criterios.amenidades,
            'riesgos_de_avenida': criterios.riesgos_de_avenida,
            'atractivos_turisticos': criterios.atractivos_turisticos,
            'espacios_publicos': criterios.espacios_publicos,
            'paradas_transporte_publico': criterios.paradas_transporte_publico,
            'establecimientos_comerciales': criterios.establecimientos_comerciales,
            'establecimientos_educativos': criterios.establecimientos_educativos,
        }
        total_puntuacion = 0
        total_pesos = 0
        for key, value in pesos.items():
            total_puntuacion += value * 5
            total_pesos += 5

        score = total_puntuacion / total_pesos

        resultados.append({
            'inmueble': inmueble.nombre,
            'direccion': inmueble.direccion,
            'score': score,
        })

    # Sort results by score
    resultados_ordenados = sorted(resultados, key=lambda x: x['score'], reverse=True)

    return Response(resultados_ordenados)

# Connect to the Avalanche Fuji Testnet
w3 = Web3(Web3.HTTPProvider(settings.AVALANCHE_RPC_URL))

# ABI of the deployed contract
contract_abi = [
    {
      "inputs": [],
      "name": "numeroDePujas",
      "outputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "uint256",
          "name": "index",
          "type": "uint256"
        }
      ],
      "name": "obtenerPuja",
      "outputs": [
        {
          "internalType": "address",
          "name": "",
          "type": "address"
        },
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        },
        {
          "internalType": "string",
          "name": "",
          "type": "string"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "uint256",
          "name": "",
          "type": "uint256"
        }
      ],
      "name": "pujas",
      "outputs": [
        {
          "internalType": "address",
          "name": "arrendatario",
          "type": "address"
        },
        {
          "internalType": "uint256",
          "name": "monto",
          "type": "uint256"
        },
        {
          "internalType": "string",
          "name": "moneda",
          "type": "string"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    },
    {
      "inputs": [
        {
          "internalType": "address",
          "name": "_arrendatario",
          "type": "address"
        },
        {
          "internalType": "uint256",
          "name": "_monto",
          "type": "uint256"
        },
        {
          "internalType": "string",
          "name": "_moneda",
          "type": "string"
        }
      ],
      "name": "registrarPuja",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    }
]
contract_address = '0x2039049ee43995AfcD86A8442610Cb70d8F860de'
contract = w3.eth.contract(address=contract_address, abi=contract_abi)

# Bidding logic
@api_view(['POST'])
def crear_puja(request):
    inmueble_id = request.data.get('inmueble_id')
    arrendatario = request.user
    monto = request.data.get('monto')
    moneda = request.data.get('moneda')

    # Normal logic to create a bid in the database
    inmueble = Inmueble.objects.get(id=inmueble_id)
    Puja.objects.create(inmueble=inmueble, arrendatario=arrendatario.username, monto=monto, moneda=moneda)

    # Now register the bid on the blockchain
    nonce = w3.eth.getTransactionCount(arrendatario.direccion_wallet)
    tx = contract.functions.registrarPuja(
        arrendatario.direccion_wallet,
        int(monto),
        moneda
    ).buildTransaction({
        'chainId': 43113,  # Fuji testnet Chain ID
        'gas': 2000000,
        'gasPrice': w3.toWei('50', 'gwei'),
        'nonce': nonce,
    })

    # Sign and send the transaction
    env = environ.Env()
    environ.Env.read_env(env_file='credentials.env')
    private_key = env('PRIVATE_KEY')
    DEBUG = env.bool('DEBUG', default=True)

    try:
        signed_tx = w3.eth.account.signTransaction(tx, private_key)
        tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)
        tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

    return Response({
        "message": "Bid created and registered on the blockchain.",
        "transaction_hash": tx_receipt.transactionHash.hex(),
    })

# Exchange rate logic
def obtener_tasa_cambio(moneda='USD'):
    url = f'https://api.coingecko.com/api/v3/simple/price?ids=avalanche-2,tether&vs_currencies={moneda.lower()}'
    response = requests.get(url)
    data = response.json()

    return {
        'AVAX': data['avalanche-2'][moneda.lower()],
        'USDT': data['tether'][moneda.lower()]
    }

# Logic to convert amount to AVAX or USDT
def convertir_a_crypto(monto_fiat, cripto, moneda='USD'):
    tasa = obtener_tasa_cambio(moneda)
    return monto_fiat / tasa[cripto]

# Core wallet payment processing logic
def procesar_pago_core_wallet(arrendatario, monto, metodo_pago):
    """
    Simulates payment processing using Avalanche's Core Wallet.
    """
    wallet_address = arrendatario.direccion_wallet  # Get user's wallet address
    if not wallet_address:
        return Response({"error": "Tenant has no wallet address configured"}, status=400)

    # Here you would integrate with Avalanche Core Wallet API to process the payment
    # Simulating a successful transaction on Avalanche Core Wallet
    transaction_data = {
        'wallet_address': wallet_address,
        'amount': monto,
        'crypto': metodo_pago  # Could be AVAX or USDT
    }

    # Simulate a successful payment response
    return Response({
        "message": "Payment processed successfully.",
        "transaction_id": "1234567890abcdef",  # Simulated transaction ID
        "amount": monto,
        "payment_method": metodo_pago
    })

# Logic for renting a property immediately
@api_view(['POST'])
def arrendar_ahora(request):
    inmueble_id = request.data.get('inmueble_id')
    arrendatario_id = request.data.get('arrendatario_id')
    metodo_pago = request.data.get('metodo_pago')

    inmueble = Inmueble.objects.get(id=inmueble_id)
    arrendatario = CustomUser.objects.get(id=arrendatario_id)

    # Convert fiat amount to selected cryptocurrency
    monto = inmueble.precio_base
    monto_crypto = convertir_a_crypto(monto, metodo_pago)

    # Configure transaction
    nonce = w3.eth.getTransactionCount(arrendatario.direccion_wallet)
    transaction = {
        'to': inmueble.arrendador.direccion_wallet,  # Landlord's wallet address
        'value': w3.toWei(monto_crypto, 'ether'),  # Amount in AVAX
        'gas': 2000000,
        'gasPrice': w3.toWei('50', 'gwei'),
        'nonce': nonce,
        'chainId': 43113,  # Fuji testnet
    }

    # Sign and send the transaction
    env = environ.Env()
    environ.Env.read_env(env_file='credentials.env')
    private_key = env('PRIVATE_KEY')
    DEBUG = env.bool('DEBUG', default=True)
    signed_tx = w3.eth.account.signTransaction(transaction, private_key)
    tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)

    try:({
        "message": "Payment successful.",
        "transaction_hash": tx_receipt.transactionHash.hex(),
    })
    except Exception as e:
        return Response({"error": f"Transaction error: {str(e)}"}, status=500)

# Payment processing logic
@api_view(['POST'])
def procesar_pago(request):
    inmueble_id = request.data.get('inmueble_id')

    try:
        inmueble = Inmueble.objects.get(id=inmueble_id)
        puja_ganadora = inmueble.pujas.latest('fecha_puja')  # Get the latest bid
        monto_final = puja_ganadora.monto
        moneda = puja_ganadora.moneda

        metodo_pago = request.data.get('metodo_pago')  # 'conventional' or 'crypto'

        if metodo_pago == "crypto":
            # Convert amount to the corresponding cryptocurrency
            cripto = request.data.get('cripto')  # 'AVAX' or 'USDT'
            monto_crypto = convertir_a_crypto(monto_final, cripto, moneda)

            # Process payment with Avalanche Core Wallet
            arrendatario_id = request.data.get('arrendatario_id')
            arrendatario = CustomUser.objects.get(id=arrendatario_id)

            # Call function to process payment in cryptocurrency
            return procesar_pago_core_wallet(arrendatario, monto_crypto, cripto)

        else:
            # Process payment using conventional method
            return Response({
                "message": "Conventional payment processed successfully.",
                "amount": monto_final,
                "currency": moneda,
            })

    except Inmueble.DoesNotExist:
        return Response({"error": "Property not found"}, status=404)
    except Puja.DoesNotExist:
        return Response({"error": "No bids for this property"}, status=404)
    except CustomUser.DoesNotExist:
        return Response({"error": "Tenant not found."}, status=404)

# User registration logic
@api_view(['POST'])
def register(request):
    form = CustomUser(request.POST, request.FILES)  # Ensure files are passed if there are photos
    if form.is_valid():
        try:
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])
            user.direccion_wallet = form.cleaned_data['direccion_wallet']  # Save wallet address
            user.save()
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            response = JsonResponse({
                'success': True,
                'access_token': access_token,
                'message': 'User registered successfully',
                'user_id': user.id,
                'username': user.username
            })
            response.set_cookie(
                'refresh_token',
                refresh_token,
                max_age=3600 * 24 * 14,
                httponly=True,
                secure=True,
                samesite='Lax'
            )
            return response
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return JsonResponse({'error': form.errors}, status=status.HTTP_400_BAD_REQUEST)

# User login logic
@api_view(['POST'])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    if not username or not password:
        return JsonResponse({'error': 'Username and password are required'}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is not None:
        django_login(request, user)
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        response = JsonResponse({
            'success': True,
            'access_token': access_token,
            'message': 'User logged in successfully',
            'user_id': user.id,
            'username': user.username
        })
        response.set_cookie(
            'refresh_token',
            refresh_token,
            max_age=3600 * 24 * 14,
            httponly=True,
            secure=True,
            samesite='Lax'
        )
        return response
    else:
        return JsonResponse({'error': 'Invalid credentials'}, status=400)
