"""noobcash URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path

from noobcash.backend.views import *

urlpatterns = [
    # connections
    path('init_server/', InitAsServer.as_view()),
    path('init_client/', InitAsClient.as_view()),
    path('client_connect/', ClientConnect.as_view()),
    path('client_accepted/', ClientAccepted.as_view()),

    # get information
    path('get_blockchain/', GetBlockchain.as_view()),
    path('get_balance/', GetBalance.as_view()),
    path('get_balance_latest/', GetLatestBalance.as_view()),
    path('get_transactions/', GetTransactions.as_view()),
    path('get_transactions_all/', GetAllTransactions.as_view()),
    path('get_num_blocks_created/', GetTotalBlocksCreated.as_view()),
    path('get_num_pending_transactions/', GetNumPendingTransactions.as_view()),
    path('get_pending_transactions/', GetPendingTransactions.as_view()),

    # receive
    path('receive_transaction/', ReceiveTransaction.as_view()),
    path('receive_block/', ReceiveBlock.as_view()),

    # send
    path('create_transaction/', CreateAndSendTransaction.as_view()),
    path('create_block/', CreateAndSendBlock.as_view())
]
