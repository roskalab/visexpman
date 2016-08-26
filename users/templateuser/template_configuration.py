class TemplateConfig(Configuration.PresentinatorConfig):
    
    def _set_user_parameters(self):

        self._set_parameters_from_locals(locals())        
        
