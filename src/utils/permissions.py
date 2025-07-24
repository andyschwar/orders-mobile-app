import json
import os
from typing import Dict, Any, List, Optional
from src.models.database import UserRole

class PermissionsManager:
    """Manages role-based access control"""
    
    def __init__(self):
        self.permissions_file = "role_permissions.json"
        self.permissions_data = {}
        self.load_permissions()
        
    def load_permissions(self):
        """Load permissions from file"""
        if os.path.exists(self.permissions_file):
            try:
                with open(self.permissions_file, 'r') as f:
                    self.permissions_data = json.load(f)
            except Exception:
                self.load_default_permissions()
        else:
            self.load_default_permissions()
            
    def load_default_permissions(self):
        """Load default permissions from template"""
        template_file = "role_permissions_template.json"
        if os.path.exists(template_file):
            try:
                with open(template_file, 'r') as f:
                    self.permissions_data = json.load(f)
            except Exception:
                self.create_default_permissions()
        else:
            self.create_default_permissions()
            
    def create_default_permissions(self):
        """Create basic default permissions"""
        self.permissions_data = {
            "role_permissions": {
                "admin": {"permissions": {}},
                "manager": {"permissions": {}},
                "user": {"permissions": {}},
                "viewer": {"permissions": {}}
            },
            "tab_access": {},
            "feature_access": {}
        }
        
    def get_user_permissions(self, user) -> Dict[str, Any]:
        """Get permissions for a specific user"""
        if not user or not user.role:
            return {}
            
        role_name = user.role.value
        return self.permissions_data.get("role_permissions", {}).get(role_name, {}).get("permissions", {})
        
    def has_permission(self, user, module: str, permission: str) -> bool:
        """Check if user has specific permission"""
        if not user or not user.role:
            return False
            
        user_permissions = self.get_user_permissions(user)
        module_permissions = user_permissions.get(module, {})
        return module_permissions.get(permission, False)
        
    def can_access_column(self, user, module: str, column: str) -> bool:
        """Check if user can access specific column"""
        if not user or not user.role:
            return False
            
        user_permissions = self.get_user_permissions(user)
        module_permissions = user_permissions.get(module, {})
        columns = module_permissions.get("columns", {})
        return columns.get(column, False)
        
    def can_access_tab(self, user, tab_name: str) -> bool:
        """Check if user can access specific tab"""
        if not user or not user.role:
            return False
            
        role_name = user.role.value
        tab_access = self.permissions_data.get("tab_access", {})
        allowed_roles = tab_access.get(tab_name, [])
        return role_name in allowed_roles
        
    def can_access_feature(self, user, feature: str) -> bool:
        """Check if user can access specific feature"""
        if not user or not user.role:
            return False
            
        role_name = user.role.value
        feature_access = self.permissions_data.get("feature_access", {})
        allowed_roles = feature_access.get(feature, [])
        return role_name in allowed_roles
        
    def get_visible_columns(self, user, module: str) -> List[str]:
        """Get list of columns user can see for a module"""
        if not user or not user.role:
            return []
            
        user_permissions = self.get_user_permissions(user)
        module_permissions = user_permissions.get(module, {})
        columns = module_permissions.get("columns", {})
        
        visible_columns = []
        for column, visible in columns.items():
            if visible:
                visible_columns.append(column)
                
        return visible_columns
        
    def get_visible_tabs(self, user) -> List[str]:
        """Get list of tabs user can access"""
        if not user or not user.role:
            return []
            
        role_name = user.role.value
        tab_access = self.permissions_data.get("tab_access", {})
        
        visible_tabs = []
        for tab_name, allowed_roles in tab_access.items():
            if role_name in allowed_roles:
                visible_tabs.append(tab_name)
                
        return visible_tabs
        
    def get_available_features(self, user) -> List[str]:
        """Get list of features user can access"""
        if not user or not user.role:
            return []
            
        role_name = user.role.value
        feature_access = self.permissions_data.get("feature_access", {})
        
        available_features = []
        for feature, allowed_roles in feature_access.items():
            if role_name in allowed_roles:
                available_features.append(feature)
                
        return available_features
        
    def reload_permissions(self):
        """Reload permissions from file"""
        self.load_permissions()
        
    def get_permissions_summary(self, user) -> Dict[str, Any]:
        """Get a summary of user permissions"""
        if not user or not user.role:
            return {}
            
        return {
            "role": user.role.value,
            "visible_tabs": self.get_visible_tabs(user),
            "available_features": self.get_available_features(user),
            "module_permissions": self.get_user_permissions(user)
        }

# Global permissions manager instance
permissions_manager = PermissionsManager()

def get_permissions_manager() -> PermissionsManager:
    """Get the global permissions manager instance"""
    return permissions_manager

def has_permission(user, module: str, permission: str) -> bool:
    """Check if user has specific permission"""
    return permissions_manager.has_permission(user, module, permission)

def can_access_column(user, module: str, column: str) -> bool:
    """Check if user can access specific column"""
    return permissions_manager.can_access_column(user, module, column)

def can_access_tab(user, tab_name: str) -> bool:
    """Check if user can access specific tab"""
    return permissions_manager.can_access_tab(user, tab_name)

def can_access_feature(user, feature: str) -> bool:
    """Check if user can access specific feature"""
    return permissions_manager.can_access_feature(user, feature)

def get_visible_columns(user, module: str) -> List[str]:
    """Get list of columns user can see for a module"""
    return permissions_manager.get_visible_columns(user, module)

def get_visible_tabs(user) -> List[str]:
    """Get list of tabs user can access"""
    return permissions_manager.get_visible_tabs(user)

def get_available_features(user) -> List[str]:
    """Get list of features user can access"""
    return permissions_manager.get_available_features(user)

def reload_permissions():
    """Reload permissions from file"""
    permissions_manager.reload_permissions() 