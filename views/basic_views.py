# This file is part of VyCinity.
# 
# VyCinity is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
# 
# VyCinity is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with VyCinity. If not, see <https://www.gnu.org/licenses/>.

from django.http import Http404
from rest_framework import permissions
from rest_framework.generics import ListCreateAPIView, ListAPIView, RetrieveAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from vycinity.models.basic_models import Router, Vyos13LiveRouterConfig, Vyos13Router, Vyos13StaticConfigSection, Vyos13RouterConfig, Deployment, DEPLOYMENT_STATE_PREPARATION, DEPLOYMENT_STATE_READY
from vycinity.permissions import IsRootCustomer
from vycinity.s42.adapter import vyos13 as Vyos13Adapter
from vycinity.s42.routerconfig import vyos13 as Vyos13ConfigEntities
from vycinity.serializers.basic_serializers import Vyos13LiveRouterConfigSerializer, Vyos13RouterSerializer, Vyos13StaticConfigSectionSerializer, Vyos13RouterConfigSerializer, DeploymentSerializer, Vyos13RouterConfigDiffSerializer
from vycinity.tasks import deploy, retrieve_vyos13_live_router_config
from vycinity.views import GenericSchema


class Vyos13RouterList(ListCreateAPIView):
    '''
    Management of VyOS Routers with at least version 1.3.0
    '''
    schema = GenericSchema(serializer=Vyos13RouterSerializer, tags=['router', 'vyos 1.3'], operation_id_base='Vyos13Router', component_name='Vyos13Router')
    permission_classes = [IsRootCustomer]
    serializer_class = Vyos13RouterSerializer
    queryset = Vyos13Router.objects.all().order_by('name')
    search_fields = ['name', 'loopback']

    def perform_create(self, serializer):
        serializer.validated_data['deploy'] = False
        super().perform_create(serializer)


class Vyos13RouterDetailView(RetrieveUpdateDestroyAPIView):
    '''
    Management of VyOS Routers with at least version 1.3.0
    '''
    schema = GenericSchema(serializer=Vyos13RouterSerializer, tags=['router', 'vyos 1.3'], operation_id_base='Vyos13Router', component_name='Vyos13Router')
    permission_classes = [IsRootCustomer]
    serializer_class = Vyos13RouterSerializer
    queryset = Vyos13Router.objects.all()
    
    def perform_update(self, serializer):
        if not isinstance(serializer, self.get_serializer_class()):
            raise AssertionError('got unexpected serializer type {}'.format(type(serializer)))
        if not isinstance(serializer.validated_data, dict):
            raise AssertionError('serializer did not seem to validate the data to save now.')
        trigger_deploy = False
        if ('active_static_configs' in serializer.validated_data and serializer.validated_data['active_static_configs'] != serializer.instance.active_static_configs) or (not serializer.instance.deploy and serializer.validated_data['deploy']):
            trigger_deploy = True
        super().perform_update(serializer)
        if trigger_deploy == True and serializer.instance.deploy:
            deployment = Deployment(change='changed router', state=DEPLOYMENT_STATE_PREPARATION)
            deployment.save()
            generated_config = Vyos13Adapter.generateConfig(serializer.instance)
            config = Vyos13RouterConfig.objects.create(router=serializer.instance, config=generated_config.config)
            deployment.configs.add(config)
            deployment.state = DEPLOYMENT_STATE_READY
            deployment.save()
            deploy.delay(deployment.pk)


class Vyos13RouterDeployView(APIView):
    '''
    Trigger a deployment of a single router. No data required in the body, an empty object is okay. The body will be ignored.
    '''
    schema = GenericSchema(serializer=DeploymentSerializer, tags=['router', 'vyos 1.3'], operation_id_base='Vyos13Router', component_name='Vyos13Router')
    permission_classes = [IsRootCustomer]

    def post(self, request, id, format=None):
        try:
            result = Vyos13Router.objects.get(pk=id)
            deployment = Deployment.objects.create(change='triggered router', state=DEPLOYMENT_STATE_PREPARATION)
            generated_config = Vyos13Adapter.generateConfig(result)
            config = Vyos13RouterConfig.objects.create(router=result, config=generated_config.config)
            deployment.configs.add(config)
            deployment.state = DEPLOYMENT_STATE_READY
            deployment.save()

            deploy.delay(deployment.pk)
            return Response(DeploymentSerializer(deployment).data, status=status.HTTP_202_ACCEPTED)
        except (Vyos13Router.DoesNotExist):
            raise Http404()

class Vyos13RouterLiveConfigListView(ListCreateAPIView):
    '''
    Display and retrieval of live configuration from a vyos13 router. Retrieval is paginated.
    '''
    schema = GenericSchema(serializer=Vyos13LiveRouterConfigSerializer, tags=['router', 'vyos 1.3'], operation_id_base='Vyos13LiveRouterConfig', component_name='Vyos13LiveRouterConfig')
    permission_classes = [IsRootCustomer]
    serializer_class = Vyos13LiveRouterConfigSerializer

    def get_queryset(self):
        router_id = self.kwargs['router_id']
        try:
            router = Vyos13Router.objects.get(pk=router_id)
            configs = Vyos13LiveRouterConfig.objects.filter(router=router).order_by('-retrieved')
            return configs
        except (Vyos13Router.DoesNotExist):
            raise Http404()
    
    def create(self, request, *args, **kwargs):
        router_id = kwargs['router_id']
        try:
            router = Vyos13Router.objects.get(pk=router_id)
            newLrc: Vyos13LiveRouterConfig = Vyos13LiveRouterConfig.objects.create(router=router)
            serializer = self.get_serializer_class()(newLrc)

            retrieve_vyos13_live_router_config.delay(newLrc.id)
            
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED, headers=headers)
        except (Vyos13Router.DoesNotExist):
            raise Http404()

class Vyos13RouterLiveConfigDetailView(APIView):
    '''
    Display of live configuration from a vyos13 router
    '''
    schema = GenericSchema(serializer=Vyos13LiveRouterConfigSerializer, tags=['router', 'vyos 1.3'], operation_id_base='Vyos13LiveRouterConfig', component_name='Vyos13LiveRouterConfig')
    permission_classes = [IsRootCustomer]

    def get(self, request, router_id, lrc_id, format=None):
        try:
            router = Vyos13Router.objects.get(pk=router_id)
            lrc = Vyos13LiveRouterConfig.objects.get(pk=lrc_id)
            if (lrc.router != router):
                raise Vyos13LiveRouterConfig.DoesNotExist()
            serializer = Vyos13LiveRouterConfigSerializer(lrc)
            return Response(data=serializer.data)
        except (Vyos13Router.DoesNotExist, Vyos13LiveRouterConfig.DoesNotExist):
            raise Http404()

class Vyos13RouterConfigDiffDetailView(APIView):
    '''
    Display of diff to live configuration from a vyos13 router. Left side of the diff is the part, which will be removed, right side ist the part that will be added, when deploying.
    '''
    schema = GenericSchema(serializer=Vyos13RouterConfigDiffSerializer, tags=['router', 'vyos 1.3'], operation_id_base='Vyos13LiveRouterConfig', component_name='Vyos13LiveRouterConfig')
    permission_classes = [IsRootCustomer]

    def get(self, request, router_id, lrc_id, format=None):
        try:
            router = Vyos13Router.objects.get(pk=router_id)
            lrc = Vyos13LiveRouterConfig.objects.get(pk=lrc_id)
            if (lrc.router != router):
                raise Vyos13LiveRouterConfig.DoesNotExist()
            
            generated_config = Vyos13Adapter.generateConfig(router)
            if lrc.config is None:
                return Response(data={'message': 'router config is not available yet'}, status=status.HTTP_400_BAD_REQUEST)
            retrieved_config = Vyos13ConfigEntities.Vyos13RouterConfig([], lrc.config)
            serializer = Vyos13RouterConfigDiffSerializer(retrieved_config.diff(generated_config))
            return Response(serializer.data)
        except (Vyos13Router.DoesNotExist, Vyos13LiveRouterConfig.DoesNotExist):
            raise Http404()

class Vyos13StaticConfigSectionList(ListCreateAPIView):
    '''
    Management of static configuration sections for VyOS 1.3
    '''
    schema = GenericSchema(serializer=Vyos13StaticConfigSectionSerializer, tags=['static config section', 'vyos 1.3'], operation_id_base='Vyos13StaticConfigSection', component_name='Vyos13StaticConfigSection')
    permission_classes = [IsRootCustomer]
    serializer_class = Vyos13StaticConfigSectionSerializer
    queryset = Vyos13StaticConfigSection.objects.all().order_by('description')


class Vyos13StaticConfigSectionDetail(APIView):
    '''
    Management of static configuration sections for VyOS 1.3
    '''
    schema = GenericSchema(serializer=Vyos13StaticConfigSectionSerializer, tags=['static config section', 'vyos 1.3'], operation_id_base='Vyos13StaticConfigSection', component_name='Vyos13StaticConfigSection')
    permission_classes = [IsRootCustomer]

    def get(self, request, id, format=None):
        try:
            result = Vyos13StaticConfigSection.objects.get(pk=id)
            serializer = Vyos13StaticConfigSectionSerializer(result)
            return Response(serializer.data)
        except Vyos13StaticConfigSection.DoesNotExist:
            raise Http404()
    
    def put(self, request, id, format=None):
        try:
            result = Vyos13StaticConfigSection.objects.get(pk=id)
            serializer = Vyos13StaticConfigSectionSerializer(result, data=request.data)
            if serializer.is_valid():
                serializer.save()

                routers = Vyos13Router.objects.filter(active_static_configs__in=[result]).distinct()
                deployment = Deployment(state=DEPLOYMENT_STATE_PREPARATION, change='change static_config_section')
                deployment.save()
                for router in routers:
                    generated_config = Vyos13Adapter.generateConfig(router)
                    config = Vyos13RouterConfig(router=router, config=generated_config.config)
                    config.save()
                    deployment.configs.add(config)
                deployment.state = DEPLOYMENT_STATE_READY
                deployment.save()

                deploy.delay(deployment.pk)

                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Vyos13StaticConfigSection.DoesNotExist:
            raise Http404()

    def delete(self, request, id, format=None):
        try:
            result = Vyos13StaticConfigSection.objects.get(pk=id)
            result.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Vyos13StaticConfigSection.DoesNotExist:
            raise Http404()


class DeploymentList(ListAPIView):
    '''
    get:
        Retrieve information about triggered deployments to routers.
    '''
    schema = GenericSchema(serializer=DeploymentSerializer, tags=['deployment'], operation_id_base='Deployment', component_name='Deployment')
    permission_classes = [IsRootCustomer]
    queryset = Deployment.objects.all()
    serializer_class = DeploymentSerializer

class DeploymentDetail(RetrieveAPIView):
    '''
    get:
        Retrieve information about triggered deployments to routers.
    '''
    schema = GenericSchema(serializer=DeploymentSerializer, tags=['deployment'], operation_id_base='Deployment', component_name='Deployment')
    permission_classes = [IsRootCustomer]
    lookup_field = 'id'
    queryset = Deployment.objects.all()
    serializer_class = DeploymentSerializer


class Vyos13RouterConfigList(ListAPIView):
    '''
    get:
        The list for configuration for VyOS 1.3 routers
    '''
    schema = GenericSchema(serializer=Vyos13RouterConfigSerializer, tags=['router', 'vyos 1.3', 'configuration'], operation_id_base='Vyos13RouterConfig', component_name='Vyos13RouterConfig')
    permission_classes = [IsRootCustomer]
    queryset = Vyos13RouterConfig.objects.all()
    serializer_class = Vyos13RouterConfigSerializer

class Vyos13RouterConfigDetail(RetrieveAPIView):
    '''
    get:
        A specific configuration for a VyOS 1.3 router
    '''
    schema = GenericSchema(serializer=Vyos13RouterConfigSerializer, tags=['router', 'vyos 1.3', 'configuration'], operation_id_base='Vyos13RouterConfig', component_name='Vyos13RouterConfig')
    permission_classes = [IsRootCustomer]
    lookup_field = 'id'
    queryset = Vyos13RouterConfig.objects.all()
    serializer_class = Vyos13RouterConfigSerializer

