/**
 * Home Screen - Dashboard for MDx Vision
 */

import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';

import { useAuthStore } from '../store/authStore';
import { colors, typography, spacing } from '../utils/theme';

export const HomeScreen: React.FC = () => {
  const navigation = useNavigation();
  const user = useAuthStore((state) => state.user);

  const quickActions = [
    { title: 'Start Session', screen: 'Session', icon: '🎙️' },
    { title: 'View Patients', screen: 'Patients', icon: '👥' },
    { title: 'Recent Notes', screen: 'Notes', icon: '📝' },
    { title: 'Settings', screen: 'Settings', icon: '⚙️' },
  ];

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.greeting}>Welcome back,</Text>
          <Text style={styles.userName}>
            {user?.firstName || 'Provider'}
          </Text>
        </View>

        {/* Stats Cards */}
        <View style={styles.statsRow}>
          <View style={styles.statCard}>
            <Text style={styles.statNumber}>0</Text>
            <Text style={styles.statLabel}>Sessions Today</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statNumber}>0</Text>
            <Text style={styles.statLabel}>Patients Seen</Text>
          </View>
        </View>

        {/* Quick Actions */}
        <Text style={styles.sectionTitle}>Quick Actions</Text>
        <View style={styles.actionsGrid}>
          {quickActions.map((action, index) => (
            <TouchableOpacity
              key={index}
              style={styles.actionCard}
              onPress={() => navigation.navigate(action.screen as never)}
            >
              <Text style={styles.actionIcon}>{action.icon}</Text>
              <Text style={styles.actionTitle}>{action.title}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Start Session CTA */}
        <TouchableOpacity
          style={styles.ctaButton}
          onPress={() => navigation.navigate('Session' as never)}
        >
          <Text style={styles.ctaText}>Start New Session</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    padding: spacing.md,
  },
  header: {
    marginBottom: spacing.lg,
  },
  greeting: {
    ...typography.body,
    color: colors.textSecondary,
  },
  userName: {
    ...typography.h1,
    color: colors.text,
  },
  statsRow: {
    flexDirection: 'row',
    gap: spacing.md,
    marginBottom: spacing.lg,
  },
  statCard: {
    flex: 1,
    backgroundColor: colors.surface,
    padding: spacing.md,
    borderRadius: 12,
    alignItems: 'center',
  },
  statNumber: {
    ...typography.h1,
    color: colors.primary,
  },
  statLabel: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  sectionTitle: {
    ...typography.h3,
    color: colors.text,
    marginBottom: spacing.md,
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
    marginBottom: spacing.lg,
  },
  actionCard: {
    width: '47%',
    backgroundColor: colors.surface,
    padding: spacing.md,
    borderRadius: 12,
    alignItems: 'center',
  },
  actionIcon: {
    fontSize: 32,
    marginBottom: spacing.sm,
  },
  actionTitle: {
    ...typography.bodySmall,
    color: colors.text,
  },
  ctaButton: {
    backgroundColor: colors.primary,
    padding: spacing.md,
    borderRadius: 12,
    alignItems: 'center',
  },
  ctaText: {
    ...typography.button,
    color: colors.background,
  },
});
