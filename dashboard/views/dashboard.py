from django.shortcuts import render, redirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.models import User
import logging
from dashboard.models import CASH, BankDeposit, Commission, Customer, CustomerDeposit, MINUS, MyDeposite, OPC, OpeningInformation, PCC, Purchase, Revenue, Sell
from django.db.models import Sum
from datetime import datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse

class DashboardView(LoginRequiredMixin, View):

    def get(self, request):
        stock= OpeningInformation.objects.first()
        pcc_stock = stock.pcc
        opc_stock = stock.opc
        total_purchase_quantity = Purchase.objects.values('cement_type').order_by('cement_type').annotate(quantity=Sum('quantity'))
        total_sell_quantity = Sell.objects.values('cement_type').order_by('cement_type').annotate(quantity=Sum('quantity'))

        top_10_customer =  Sell.objects.values('customer__name').annotate(quantity=Sum('quantity'), total_buy=Sum('total_bill')).order_by('-total_buy')
        print(top_10_customer)

        if total_purchase_quantity.exists():
            for quantity in total_purchase_quantity:
                if quantity.get('cement_type') == OPC:
                    opc_stock+= quantity.get('quantity')
                else:
                    pcc_stock+= quantity.get('quantity')

        if total_sell_quantity.exists():
            for quantity in total_sell_quantity:
                if quantity.get('cement_type') == OPC:
                    opc_stock-= quantity.get('quantity')
                else:
                    pcc_stock-= quantity.get('quantity')

        opening_balance = 0
        opening_information = OpeningInformation.objects.first()
        if opening_information:
            opening_balance = -opening_information.my_balance if opening_information.my_balance_type == MINUS else opening_information.my_balance
        
        total_buy= Purchase.objects.all().aggregate(Sum('sub_total'))
        total_buy =  total_buy.get('sub_total__sum') if  total_buy.get('sub_total__sum') else 0


        total_deposit = MyDeposite.objects.all().aggregate(Sum('amount'))
        total_deposit =  total_deposit.get('amount__sum') if total_deposit.get('amount__sum') else 0


        total_commission = Commission.objects.all().aggregate(Sum('amount'))
        total_commission =  total_commission.get('amount__sum') if total_commission.get('amount__sum') else 0
        


        my_balance = 0
        my_due = 0
        balance =  (opening_balance - total_buy) + total_commission + total_deposit
        if balance > 0:
            my_balance = balance
        else:
            my_due = balance


        context = {
            'pcc_stock': pcc_stock,
            'opc_stock': opc_stock,
            'my_balance': my_balance,
            'my_due': my_due,
            'top_10_customer': top_10_customer

        }
        return render(request, 'dashboard.html', context) 

class RevenueView(LoginRequiredMixin, View):

    def get(self, request):
        customer= Customer.objects.all()
        revenue= Revenue.objects.all()
        return render(request, 'revenue.html',{'revenue': revenue, 'customer': customer})

class GenerateRevenueView(LoginRequiredMixin, View):
    def post(self, request):
        month_data= request.POST.get('month')
        pcc= request.POST.get('pcc')
        opc= request.POST.get('opc')

        month, year= month_data.split('-')[1], month_data.split('-')[0]

        sell= Sell.objects.all()
        for i in Customer.objects.all():
            cus_rev= Revenue.objects.filter(customer= i, date__month= month, date__year= year)
            if cus_rev:
                rev_object= cus_rev.first()
            else:
                rev_object= Revenue()
            customer_sell= sell.filter(created_at__month=  month, created_at__year= year, customer= i)
            rev_object.customer= i
            rev_object.date=  datetime.strptime(month_data+ '-30', "%Y-%m-%d").date()
            revenue= 0
            if customer_sell.exists():
                pcc_sell= customer_sell.filter(cement_type= PCC)
                if pcc_sell.exists():
                    pcc_value= pcc_sell.aggregate(total_quantity=Sum('quantity'), total_bill= Sum('total_bill'))
                    pcc_total_quantity= pcc_value.get('total_quantity')
                    pcc_total_bill= pcc_value.get('total_bill')
                    print(i.name, pcc_total_bill, pcc_total_quantity )

                    rev_object.pcc_sell= pcc_total_bill
                    rev_object.pcc_purchase= int(pcc) * pcc_total_quantity
                    revenue+= pcc_total_bill - (int(pcc) * pcc_total_quantity)
                   
                opc_sell= customer_sell.filter(cement_type= OPC)
                if opc_sell.exists():
                    opc_value=opc_sell.aggregate(total_quantity=Sum('quantity'), total_bill= Sum('total_bill'))
                    print(opc_value, i.name, 'opcccccc')
                    opc_total_quantity= opc_value.get('total_quantity')
                    opc_total_bill= opc_value.get('total_bill')

                    rev_object.opc_sell= opc_total_bill
                    rev_object.opc_purchase= int(opc) * opc_total_quantity
                    revenue+= opc_total_bill - (int(opc) * opc_total_quantity)
    
                rev_object.revenue= revenue
                rev_object.save()
            else:
                rev_object.save()
        return redirect('dashboard:revenue_url')

class RemoveView(View):

    def get(self, request):
        data= request.GET
        print(data)
        sector= data.get('sector')
        id_= data.get('id')
        if sector == '1':
            model= Sell
        if sector == '2':
            model= CustomerDeposit
        if sector == '3':
            model= Purchase
        if sector == '4':
            model= MyDeposite
        if sector == '5':
            model= Commission
        if sector == '6':
            model= Customer
        if sector == '7':
            model= BankDeposit
        model.objects.get(id= id_).delete()
        return JsonResponse({'id': id_})


class OpeningInfoView(View):

    def get(self, request):
        opening_info = OpeningInformation.objects.first()
        return render(request, 'opening_info.html', {'opening_info': opening_info})

    
    def post(self, request):
        data = request.POST
        opc= data.get('opc')
        pcc= data.get('pcc')
        op_balance_type= data.get('op_balance_type')
        opening_balance= data.get('opening_balance')
        cash_amount= data.get('cash_amount')
        aibl_amount= data.get('aibl_amount')
        sibl_amount= data.get('sibl_amount')
        asia_amount= data.get('asia_amount')

        opening_info = OpeningInformation.objects.first()
        if not opening_info:
            opening_info = OpeningInformation()
        
        opening_info.my_balance_type = op_balance_type
        opening_info.my_balance = opening_balance
        opening_info.pcc = pcc
        opening_info.opc = opc
        opening_info.cash_amount = cash_amount
        opening_info.aibl_amount = aibl_amount
        opening_info.sibl_amount = sibl_amount
        opening_info.asia_amount = asia_amount

        opening_info.save() 
        return redirect('dashboard:opening_info_url')



class AccountView(View):

    def get(self, request):
        openinf_info = OpeningInformation.objects.values().first()
        cash_amount = openinf_info.get('cash_amount')
        aibl_amount = openinf_info.get('aibl_amount')
        sibl_amount = openinf_info.get('sibl_amount')
        asia_amount = openinf_info.get('asia_amount')

        paid_amount = Sell.objects.filter(balance_sector = CASH).aggregate(Sum('paid_amount')).get('paid_amount__sum')
        if not paid_amount:
            paid_amount = 0

        customer_deposit = CustomerDeposit.objects.filter(balance_sector = CASH).aggregate(Sum('amount')).get('amount__sum')
        if not customer_deposit:
            customer_deposit = 0


        bank_depo = BankDeposit.objects.values('account').order_by('account').annotate(total_price=Sum('amount'))
        aibl_depo= 0
        sibl_depo = 0
        asia_dipo = 0
        for i in bank_depo:
            if i.get('account') == 3:
                aibl_depo = i.get('total_price')
            if i.get('account') == 4:
                sibl_depo = i.get('total_price')
            if i.get('account') == 5:
                asia_dipo = i.get('total_price')
       
        purchases = Purchase.objects.values('balance_sector').order_by('balance_sector').annotate(total_price=Sum('sub_total'))
        cash_purchae= 0
        aibl_purchase= 0
        sibl_purchase = 0
        asia_purchase = 0
        for i in purchases:
            if i.get('balance_sector') == 2:
                cash_purchae = i.get('total_price')
            if i.get('balance_sector') == 3:
                aibl_purchase = i.get('total_price')            
            if i.get('balance_sector') == 4:
                sibl_purchase = i.get('total_price')            
            if i.get('balance_sector') == 5:
                asia_purchase = i.get('total_price')            


        total_cash = (cash_amount + paid_amount + customer_deposit) - (cash_purchae + aibl_depo + sibl_depo + asia_dipo)
        total_aibl_amount = (aibl_amount + aibl_depo) - aibl_purchase
        total_sibl_amount = (sibl_amount + sibl_depo) - sibl_purchase
        total_asia_amount = (asia_amount + asia_dipo) - asia_purchase

        context = {
            'total_cash': total_cash,
            "total_aibl_amount":total_aibl_amount,
            "total_sibl_amount":total_sibl_amount,
            "total_asia_amount":total_asia_amount,

        }
        return render(request, 'account.html', context)

