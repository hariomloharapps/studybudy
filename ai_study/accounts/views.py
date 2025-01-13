# accounts/exceptions.py
from rest_framework.exceptions import APIException
from rest_framework import status

class InvalidUUIDError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid UUID format"

class UserNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "User not found"

class InsufficientBalanceError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Insufficient balance for this transaction"

class InvalidAmountError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid amount provided"

class InvalidTransactionTypeError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid transaction type"

# accounts/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import UserAccount, Transaction
from .serializers import TransactionSerializer, UserAccountSerializer
# from .exceptions import *
import uuid
import decimal
from django.db.models import Q
from datetime import datetime

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

    def validate_uuid(self, user_uuid):
        try:
            return uuid.UUID(str(user_uuid))
        except (ValueError, AttributeError, TypeError):
            raise InvalidUUIDError(detail="Invalid UUID format provided")

    def validate_amount(self, amount):
        try:
            decimal_amount = decimal.Decimal(str(amount))
            if decimal_amount <= 0:
                raise InvalidAmountError(detail="Amount must be greater than 0")
            return decimal_amount
        except decimal.InvalidOperation:
            raise InvalidAmountError(detail="Invalid amount format provided")

    def validate_transaction_type(self, transaction_type, is_credit=True):
        credit_types = ['coin_credited_by_ads', 'coin_credited_by_purchase', 'coin_credited_by_redeem']
        spend_types = ['coin_spend']
        
        if is_credit and transaction_type not in credit_types:
            raise InvalidTransactionTypeError(
                detail=f"Invalid credit transaction type. Must be one of: {', '.join(credit_types)}"
            )
        elif not is_credit and transaction_type not in spend_types:
            raise InvalidTransactionTypeError(
                detail=f"Invalid spend transaction type. Must be: coin_spend"
            )

    def get_user_account(self, user_uuid):
        try:
            validated_uuid = self.validate_uuid(user_uuid)
            user_account = UserAccount.objects.select_for_update().get(
                user__uuid=validated_uuid
            )
            return user_account
        except UserAccount.DoesNotExist:
            raise UserNotFoundError(detail=f"No user account found for UUID: {user_uuid}")

    @action(detail=False, methods=['post'])
    def credit_coins(self, request):
        try:
            # Validate required fields
            required_fields = ['user_uuid', 'amount', 'transaction_type']
            missing_fields = [field for field in required_fields if field not in request.data]
            if missing_fields:
                return Response(
                    {"error": f"Missing required fields: {', '.join(missing_fields)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Extract and validate data
            user_uuid = request.data['user_uuid']
            amount = self.validate_amount(request.data['amount'])
            transaction_type = request.data['transaction_type']
            description = request.data.get('description', '')

            # Validate transaction type
            self.validate_transaction_type(transaction_type, is_credit=True)

            # Get user account with lock for atomic operation
            with transaction.atomic():
                user_account = self.get_user_account(user_uuid)
                
                # Create transaction
                new_transaction = Transaction.objects.create(
                    account=user_account,
                    transaction_type=transaction_type,
                    amount=amount,
                    description=description
                )

                # Update account balance
                user_account.balance += amount
                user_account.last_transaction_time = timezone.now()
                user_account.save()

            return Response(
                {
                    "message": "Transaction completed successfully",
                    "transaction": TransactionSerializer(new_transaction).data,
                    "new_balance": str(user_account.balance)
                },
                status=status.HTTP_201_CREATED
            )

        except (InvalidUUIDError, UserNotFoundError, InvalidAmountError,
                InvalidTransactionTypeError) as e:
            return Response({"error": str(e)}, status=e.status_code)
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def spend_coins(self, request):
        try:
            # Validate required fields
            required_fields = ['user_uuid', 'amount']
            missing_fields = [field for field in required_fields if field not in request.data]
            if missing_fields:
                return Response(
                    {"error": f"Missing required fields: {', '.join(missing_fields)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Extract and validate data
            user_uuid = request.data['user_uuid']
            amount = self.validate_amount(request.data['amount'])
            description = request.data.get('description', '')

            # Get user account with lock for atomic operation
            with transaction.atomic():
                user_account = self.get_user_account(user_uuid)

                # Check balance
                if user_account.balance < amount:
                    raise InsufficientBalanceError(
                        detail=f"Insufficient balance. Current balance: {user_account.balance}, Required: {amount}"
                    )

                # Create transaction
                new_transaction = Transaction.objects.create(
                    account=user_account,
                    transaction_type='coin_spend',
                    amount=-amount,
                    description=description
                )

                # Update account balance
                user_account.balance -= amount
                user_account.last_transaction_time = timezone.now()
                user_account.save()

            return Response(
                {
                    "message": "Transaction completed successfully",
                    "transaction": TransactionSerializer(new_transaction).data,
                    "new_balance": str(user_account.balance)
                },
                status=status.HTTP_201_CREATED
            )

        except (InvalidUUIDError, UserNotFoundError, InvalidAmountError,
                InsufficientBalanceError) as e:
            return Response({"error": str(e)}, status=e.status_code)
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def transaction_history(self, request):
        try:
            user_uuid = request.query_params.get('user_uuid')
            if not user_uuid:
                return Response(
                    {"error": "user_uuid is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate UUID and get user account
            user_account = self.get_user_account(user_uuid)

            # Get optional filter parameters
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            transaction_type = request.query_params.get('transaction_type')

            # Build query
            transactions = Transaction.objects.filter(account=user_account)

            if start_date:
                try:
                    start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                    transactions = transactions.filter(timestamp__gte=start_datetime)
                except ValueError:
                    return Response(
                        {"error": "Invalid start_date format. Use YYYY-MM-DD"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            if end_date:
                try:
                    end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                    transactions = transactions.filter(timestamp__lte=end_datetime)
                except ValueError:
                    return Response(
                        {"error": "Invalid end_date format. Use YYYY-MM-DD"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            if transaction_type:
                transactions = transactions.filter(transaction_type=transaction_type)

            return Response(
                {
                    "user_uuid": str(user_uuid),
                    "current_balance": str(user_account.balance),
                    "transactions": TransactionSerializer(transactions, many=True).data
                },
                status=status.HTTP_200_OK
            )

        except (InvalidUUIDError, UserNotFoundError) as e:
            return Response({"error": str(e)}, status=e.status_code)
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        









# accounts/views.py
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from app.models import User
from .models import RedeemCode, Transaction
from .serializers import RedeemCodeRequestSerializer, RedeemCodeResponseSerializer
from django.shortcuts import get_object_or_404

@api_view(['POST'])
def redeem_code(request):
    # Get user UUID from query parameters
    user_uuid = request.query_params.get('uuid')
    if not user_uuid:
        return Response(
            {'error': 'User UUID is required as a query parameter'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate request body
    serializer = RedeemCodeRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Get user and code
    user = get_object_or_404(User, uuid=user_uuid)
    try:
        redeem_code = RedeemCode.objects.get(code=serializer.validated_data['code'])
    except RedeemCode.DoesNotExist:
        return Response(
            {'error': 'Invalid redeem code'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check if code is valid
    if not redeem_code.is_valid():
        return Response(
            {'error': 'Code is expired or already used'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Update code status
    redeem_code.is_used = True
    redeem_code.used_at = timezone.now()
    redeem_code.user = user
    redeem_code.save()

    # Update user account balance
    user_account = user.useraccount
    user_account.balance += redeem_code.amount
    user_account.last_transaction_time = timezone.now()
    user_account.save()

    # Create transaction record
    Transaction.objects.create(
        account=user_account,
        transaction_type='coin_credited_by_redeem',
        amount=redeem_code.amount,
        description=f'Redeem code: {redeem_code.code}'
    )

    # Return response
    response_serializer = RedeemCodeResponseSerializer(redeem_code)
    return Response(response_serializer.data, status=status.HTTP_200_OK)
