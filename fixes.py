from pathlib import Path
p=Path('core/api.py')
s=p.read_text(encoding='utf-8-sig')
s=s.replace("variants=VariantSerializer(many=True,read_only=True)","variants=serializers.SerializerMethodField()\n    def get_variants(self,obj):\n        values=list(obj.variants.all())\n        request=self.context.get('request')\n        params=request.query_params if request else {}\n        if not request or not request.user.is_staff: values=[v for v in values if v.active]\n        if params.get('available')=='true': values=[v for v in values if v.stock>0]\n        for key,op in [('min_price',lambda a,b:a>=b),('max_price',lambda a,b:a<=b)]:\n            if params.get(key): values=[v for v in values if op(v.price,Decimal(params[key]))]\n        return VariantSerializer(values,many=True).data")
s=s.replace("q=q.filter(**vf).annotate(min_price=Min('variants__price')).distinct()","if not self.request.user.is_staff or len(vf)>1 or p.get('available')=='true': q=q.filter(**vf)\n        q=q.annotate(min_price=Min('variants__price')).distinct()")
s=s.replace("CartItem.objects.filter(cart__user=request.user,pk=request.data.get('id')).delete()","item_id=serializers.IntegerField(min_value=1).run_validation(request.data.get('id'))\n        CartItem.objects.filter(cart__user=request.user,pk=item_id).delete()")
s=s.replace("request.user.save(update_fields=['email','username'])","try: request.user.save(update_fields=['email','username'])\n    except IntegrityError: fail('email_taken')")
p.write_text(s,encoding='utf-8')
p=Path('static/app.js');s=p.read_text(encoding='utf-8')
s=s.replace("if($('#chat-history'))await refreshMessages();","if($('#chat-history'))await refreshMessages();if(path.endsWith('/notifications/'))await notificationsPage();")
p.write_text(s,encoding='utf-8')

