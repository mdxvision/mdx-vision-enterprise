/**
 * Root Navigation for MDx Vision
 */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

// Screens
import { LoginScreen } from '../screens/auth/LoginScreen';
import { HomeScreen } from '../screens/HomeScreen';
import { PatientListScreen } from '../screens/patients/PatientListScreen';
import { PatientDetailScreen } from '../screens/patients/PatientDetailScreen';
import { SessionScreen } from '../screens/session/SessionScreen';
import { SessionRecordingScreen } from '../screens/session/SessionRecordingScreen';
import { NotesScreen } from '../screens/notes/NotesScreen';
import { SettingsScreen } from '../screens/SettingsScreen';

import { RootStackParamList, MainTabParamList } from '../types/navigation';
import { colors } from '../utils/theme';

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<MainTabParamList>();

const MainTabs: React.FC = () => {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: colors.background,
          borderTopColor: colors.border,
          height: 60,
        },
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textSecondary,
      }}
    >
      <Tab.Screen 
        name="Home" 
        component={HomeScreen}
        options={{ tabBarLabel: 'Home' }}
      />
      <Tab.Screen 
        name="Patients" 
        component={PatientListScreen}
        options={{ tabBarLabel: 'Patients' }}
      />
      <Tab.Screen 
        name="Session" 
        component={SessionScreen}
        options={{ tabBarLabel: 'Session' }}
      />
      <Tab.Screen 
        name="Settings" 
        component={SettingsScreen}
        options={{ tabBarLabel: 'Settings' }}
      />
    </Tab.Navigator>
  );
};

interface RootNavigatorProps {
  isAuthenticated: boolean;
}

export const RootNavigator: React.FC<RootNavigatorProps> = ({ isAuthenticated }) => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.background },
      }}
    >
      {!isAuthenticated ? (
        <Stack.Screen name="Login" component={LoginScreen} />
      ) : (
        <>
          <Stack.Screen name="MainTabs" component={MainTabs} />
          <Stack.Screen name="PatientDetail" component={PatientDetailScreen} />
          <Stack.Screen 
            name="SessionRecording" 
            component={SessionRecordingScreen}
            options={{ gestureEnabled: false }}
          />
          <Stack.Screen name="Notes" component={NotesScreen} />
        </>
      )}
    </Stack.Navigator>
  );
};
