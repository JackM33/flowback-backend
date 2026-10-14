import json
from pprint import pprint

from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate

from flowback.common.tests import generate_request
from flowback.group.tests.factories import GroupFactory, GroupUserFactory, GroupUserDelegateFactory, \
    GroupUserDelegatorFactory, GroupTagsFactory
from flowback.poll.models import Poll
from flowback.poll.tests.factories import PollFactory, PollProposalFactory, PollVotingTypeCardinalFactory, \
    PollDelegateVotingFactory
from flowback.poll.tests.utils import generate_poll_phase_kwargs
from flowback.poll.views.vote import DelegatePollVoteListAPI, PollProposalDelegateVoteAPI


class PollDelegateTests(APITestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.group_user_creator = GroupUserFactory(group=self.group)
        self.delegate = GroupUserDelegateFactory(group=self.group)
        self.delegator = GroupUserFactory(group=self.group)
        
        # Create additional group users with different roles for comprehensive testing
        self.regular_group_user = GroupUserFactory(group=self.group, is_admin=False)
        self.admin_group_user = GroupUserFactory(group=self.group, is_admin=True)
        self.another_regular_user = GroupUserFactory(group=self.group, is_admin=False)
        (self.poll_one,
         self.poll_two,
         self.poll_three) = [PollFactory(created_by=self.group_user_creator, poll_type=Poll.PollType.SCORE,
                                         **generate_poll_phase_kwargs('delegate_vote')) for x in range(3)]

        self.poll_one_proposals = [PollProposalFactory(poll=self.poll_one,
                                                       created_by=self.group_user_creator) for x in range(3)]
        self.poll_two_proposals = [PollProposalFactory(poll=self.poll_two,
                                                       created_by=self.group_user_creator) for x in range(3)]
        self.poll_three_proposals = [PollProposalFactory(poll=self.poll_three,
                                                         created_by=self.group_user_creator) for x in range(3)]

        (self.poll_delegate_voting_one,
         self.poll_delegate_voting_two,
         self.poll_delegate_voting_three) = [PollDelegateVotingFactory(created_by=self.delegate.pool,
                                                                       poll=poll) for poll in [self.poll_one,
                                                                                               self.poll_two,
                                                                                               self.poll_three]]

        self.poll_one_delegate_votes = [PollVotingTypeCardinalFactory(author_delegate=self.poll_delegate_voting_one,
                                                                      proposal=proposal
                                                                      ) for proposal in self.poll_one_proposals[0:2]]
        self.poll_two_delegate_votes = [PollVotingTypeCardinalFactory(author_delegate=self.poll_delegate_voting_two,
                                                                      proposal=proposal
                                                                      ) for proposal in self.poll_two_proposals[1:3]]
        self.poll_three_delegate_votes = [PollVotingTypeCardinalFactory(author_delegate=self.poll_delegate_voting_three,
                                                                        proposal=proposal)
                                          for proposal in self.poll_three_proposals[0:3:2]]

    def test_delegate_poll_vote_list(self):
        # Test as delegate user
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.delegate.group_user.user,
            data=dict(group_id=self.group.id)
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)  # Should return all 3 polls

        # Verify poll IDs are in the response
        poll_ids = [item['poll']['id'] for item in response.data['results']]
        self.assertIn(self.poll_one.id, poll_ids)
        self.assertIn(self.poll_two.id, poll_ids)
        self.assertIn(self.poll_three.id, poll_ids)

        # Test filtering by poll_id
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.delegate.group_user.user,
            data=dict(group_id=self.group.id, poll_id=self.poll_one.id)
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)  # Should return only poll_one
        self.assertEqual(response.data['results'][0]['poll']['id'], self.poll_one.id)

        # Test filtering by delegate_pool_id
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.delegate.group_user.user,
            data=dict(group_id=self.group.id, delegate_pool_id=self.delegate.pool.id)
        )

        self.assertEqual(response.status_code, 200)
        # Should return polls where this delegate has voted
        self.assertGreaterEqual(len(response.data['results']), 1)

        # Test that ALL group users have permission to preview delegate votes
        # This expands the test as requested in the issue description
        
        # Test as regular group user (non-admin, non-delegate)
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.regular_group_user.user,
            data=dict(group_id=self.group.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)  # Should return all 3 polls
        
        # Test as admin group user
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.admin_group_user.user,
            data=dict(group_id=self.group.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)  # Should return all 3 polls
        
        # Test as another regular group user
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.another_regular_user.user,
            data=dict(group_id=self.group.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)  # Should return all 3 polls
        
        # Test as delegator user
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.delegator.user,
            data=dict(group_id=self.group.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)  # Should return all 3 polls
        
        # Test as group creator
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.group_user_creator.user,
            data=dict(group_id=self.group.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)  # Should return all 3 polls
        
        # Verify that all group users can also access with filters
        # Test regular user with poll_id filter
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.regular_group_user.user,
            data=dict(group_id=self.group.id, poll_id=self.poll_two.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)  # Should return only poll_two
        self.assertEqual(response.data['results'][0]['poll']['id'], self.poll_two.id)
        
        # Test admin user with delegate_pool_id filter
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.admin_group_user.user,
            data=dict(group_id=self.group.id, delegate_pool_id=self.delegate.pool.id)
        )
        self.assertEqual(response.status_code, 200)
        # Should return polls where this delegate has voted
        self.assertGreaterEqual(len(response.data['results']), 1)


class PollUserDelegateVoteTests(APITestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.tag = GroupTagsFactory(group=self.group)
        self.other_tag = GroupTagsFactory(group=self.group)
        self.creator = GroupUserFactory(group=self.group)
        self.poll = PollFactory(created_by=self.creator, tag=self.tag, **generate_poll_phase_kwargs('vote'))
        self.proposals = [PollProposalFactory(poll=self.poll, created_by=self.creator) for x in range(2)]

        # Two delegates who both voted, so returning the wrong one shows
        self.delegate = GroupUserDelegateFactory(group=self.group)
        self.other_delegate = GroupUserDelegateFactory(group=self.group)
        for delegate, scores in [(self.delegate, [4, 1]), (self.other_delegate, [2, 5])]:
            delegate_voting = PollDelegateVotingFactory(created_by=delegate.pool, poll=self.poll)
            for proposal, score in zip(self.proposals, scores):
                PollVotingTypeCardinalFactory(author_delegate=delegate_voting, proposal=proposal, raw_score=score)

    def delegate_to(self, delegator, pool, tag):
        GroupUserDelegatorFactory(group=self.group, delegator=delegator, delegate_pool=pool).tags.add(tag)

    def get_delegate_vote(self, group_user, poll=None):
        response = generate_request(api=PollProposalDelegateVoteAPI,
                                    url_params=dict(poll=(poll or self.poll).id),
                                    user=group_user.user)
        self.assertEqual(response.status_code, 200)
        return response.data

    def assert_delegate_vote(self, data, delegate, scores):
        self.assertEqual(data['delegate_pool_id'], delegate.pool.id)
        self.assertEqual({vote['proposal_id']: vote['raw_score'] for vote in data['vote']},
                         {proposal.id: score for proposal, score in zip(self.proposals, scores)})

    def assert_no_delegate_vote(self, data):
        self.assertEqual(data, dict(delegate_pool_id=None, vote=[]))

    def test_delegator_gets_their_delegate_vote(self):
        delegator = GroupUserFactory(group=self.group)
        self.delegate_to(delegator, self.other_delegate.pool, self.tag)

        self.assert_delegate_vote(self.get_delegate_vote(delegator), self.other_delegate, [2, 5])

    def test_delegate_gets_own_vote(self):
        # Delegates get their own vote whether they self-delegated or not
        self.assert_delegate_vote(self.get_delegate_vote(self.other_delegate.group_user), self.other_delegate, [2, 5])

        self.delegate_to(self.other_delegate.group_user, self.other_delegate.pool, self.tag)
        self.assert_delegate_vote(self.get_delegate_vote(self.other_delegate.group_user), self.other_delegate, [2, 5])

    def test_member_without_delegation(self):
        self.assert_no_delegate_vote(self.get_delegate_vote(GroupUserFactory(group=self.group)))

    def test_delegator_on_other_tag(self):
        delegator = GroupUserFactory(group=self.group)
        self.delegate_to(delegator, self.delegate.pool, self.other_tag)

        self.assert_no_delegate_vote(self.get_delegate_vote(delegator))

    def test_delegate_has_not_voted(self):
        silent_delegate = GroupUserDelegateFactory(group=self.group)
        delegator = GroupUserFactory(group=self.group)
        self.delegate_to(delegator, silent_delegate.pool, self.tag)

        self.assert_no_delegate_vote(self.get_delegate_vote(delegator))

    def test_poll_without_tag(self):
        untagged_poll = PollFactory(created_by=self.creator, **generate_poll_phase_kwargs('vote'))
        PollDelegateVotingFactory(created_by=self.delegate.pool, poll=untagged_poll)
        delegator = GroupUserFactory(group=self.group)
        self.delegate_to(delegator, self.delegate.pool, self.tag)

        self.assert_no_delegate_vote(self.get_delegate_vote(delegator, untagged_poll))
