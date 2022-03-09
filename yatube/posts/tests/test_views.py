from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Follow, Group, Post

User = get_user_model()


class UserViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='test_group',
            slug='test_slug',
            description='test_description',
        )
        cls.user = User.objects.create_user(username='Test_username')
        cls.post = Post.objects.create(
            text='test_text',
            author=User.objects.get(username='Test_username'),
            group=cls.group,
            image=uploaded,
        )
        cls.user_1 = User.objects.create_user(username='username_1')
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client_1 = Client()
        cls.authorized_client.force_login(cls.user)
        cls.authorized_client_1.force_login(cls.user_1)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        cache.clear()
        post = self.post
        templates_page_names = {
            reverse('posts:main_page'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': 'test_slug'}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': 'Test_username'}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': f'{post.pk}'}):
                'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/post_create.html',
            reverse('posts:post_edit', kwargs={'post_id': f'{post.pk}'}):
                'posts/post_create.html',
        }
        for url, template in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_main_page_correct_context(self):
        """Проверка словаря context на странице main_page."""
        cache.clear()
        response = self.authorized_client.get(reverse('posts:main_page'))
        first_object = response.context['page_obj'][0]
        test_objects = {
            self.post.author.username: first_object.author.username,
            self.post.text: first_object.text,
            self.post.image: first_object.image,
        }
        for obj, expected in test_objects.items():
            with self.subTest(expected=expected):
                self.assertEqual(obj, expected)

    def test_main_page_cache(self):
        """Проверка: объекты страницы main_page кэшируются"""
        cache.clear()
        response_one = self.guest_client.get(reverse('posts:main_page'))
        response_one_obj_content = response_one.content
        response_one.context['page_obj'][0].delete()
        Post.objects.create(
            text='text',
            author=self.user,
            group=self.group
        )
        response_two = self.guest_client.get(reverse('posts:main_page'))
        response_two_obj_content = response_two.content
        self.assertEqual(response_one_obj_content, response_two_obj_content)
        cache.clear()
        response_three = self.guest_client.get(reverse('posts:main_page'))
        response_three_obj_content = response_three.content
        self.assertNotEqual(
            response_two_obj_content, response_three_obj_content
        )

    def test_group_list_page_correct_context(self):
        """Проверка словаря context на странице group_list."""
        response = self.authorized_client.get(reverse(
            'posts:group_list', args={self.group.slug})
        )
        post_obj = response.context['page_obj'][0]
        group_obj = response.context['group']
        test_objects = {
            self.group.title: group_obj.title,
            self.group.description: group_obj.description,
            self.group.slug: group_obj.slug,
            self.post.text: post_obj.text,
            self.post.image: post_obj.image,
        }
        for obj, expected in test_objects.items():
            with self.subTest(expected=expected):
                self.assertEqual(obj, expected)

    def test_profile_page_correct_context(self):
        """Проверка словаря context на странице profile."""
        response = self.authorized_client.get(reverse(
            'posts:profile', args={self.post.author.username})
        )
        post_obj = response.context['page_obj'][0]
        test_objects = {
            self.post.text: post_obj.text,
            self.post.author.username: post_obj.author.username,
            self.post.image: post_obj.image,
        }
        for obj, expected in test_objects.items():
            with self.subTest(expected=expected):
                self.assertEqual(obj, expected)

    def test_post_detail_correct_context(self):
        """Проверка отображения поста на странцие post_detail."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', args={self.post.pk})
        )
        post_obj = response.context.get('post')
        test_objects = {
            self.post.text: post_obj.text,
            self.post.author.username: post_obj.author.username,
            self.post.image: post_obj.image,
        }
        for obj, expected in test_objects.items():
            with self.subTest(expected=expected):
                self.assertEqual(obj, expected)

    def test_create_post_correct_context(self):
        """Проверка отображения поста на странцие create_post."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_correct_context(self):
        """Проверка отображения поста на странцие post_edit."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', args={self.post.pk})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_first_page_contains_ten_records(self):
        """Проверка работы пагинатора на первой странице main_page,
        group_list, profile.
        """
        cache.clear()
        for i in range(1, 15):
            self.post = Post.objects.create(
                author=self.user,
                text=f'test_text_{str(i)}',
                pub_date=Post.pub_date,
                group=UserViewTest.group,
            )
        page_content = {
            self.client.get(reverse('posts:main_page')): settings.SHOW_POSTS,
            self.client.get(
                reverse('posts:group_list', args={self.group.slug})
            ): settings.SHOW_POSTS,
            self.client.get(
                reverse('posts:profile', args={self.post.author.username})
            ): settings.SHOW_POSTS,
        }
        for response, expected in page_content.items():
            with self.subTest(response=response):
                obj = len(response.context.get('page_obj').object_list)
                self.assertEqual(obj, expected)

    def test_second_page_contains_some_records(self):
        """Проверка работы пагинатора на второй странице main_page,
        group_list, profile.
        """
        for i in range(1, 15):
            self.post = Post.objects.create(
                author=self.user,
                text=f'test_text_{str(i)}',
                pub_date=Post.pub_date,
                group=UserViewTest.group,
            )
        page_content = {
            self.client.get(reverse('posts:main_page') + '?page=2'): 5,
            self.client.get(
                reverse('posts:group_list', args={self.group.slug}) + '?page=2'
            ): 5,
            self.client.get(
                reverse('posts:profile', args={self.post.author.username})
                + '?page=2'
            ): 5,
        }
        for response, expected in page_content.items():
            with self.subTest(response=response):
                obj = len(response.context.get('page_obj').object_list)
                self.assertEqual(obj, expected)

    def test_create_post_in_his_group(self):
        """Проверка, что при создании поста,
        этот пост появляется на странице group_list.
        """
        response_1 = self.authorized_client.get(
            reverse('posts:group_list', args={self.group.slug})
        )
        obj = response_1.context.get('page_obj').object_list
        self.assertIn(self.post, obj)

    def test_create_post_not_in_his_group(self):
        """Проверка, что при создании пост не попал в группу,
        для которой не был предназначен.
        """
        group_1 = Group.objects.create(
            title='test_group_1',
            slug='test_slug_1',
            description='test_description_1',
        )
        response_2 = self.authorized_client.get(
            reverse('posts:group_list', args={group_1.slug})
        )
        obj_2 = response_2.context.get('page_obj').object_list
        self.assertNotIn(self.post, obj_2)

    def test_post_in_main_page(self):
        """Проверка, что при создании пост попадает на страницу main_page."""
        cache.clear()
        response = self.authorized_client.get(reverse('posts:main_page'))
        self.assertIn(self.post, response.context.get('page_obj').object_list)

    def test_post_in_profile(self):
        """Проверка, что при создании пост попадает на страницу profile."""
        response = self.authorized_client.get(reverse(
            'posts:profile', args={self.post.author.username})
        )
        self.assertIn(self.post, response.context.get('page_obj').object_list)

    def test_authorized_client_can_follow(self):
        """Проверка, что авторизованный пользователь может подписываться на
        других пользователей.
        """
        response_1 = self.authorized_client_1.get(
            reverse('posts:follow_index')
        )
        self.assertNotContains(response_1, self.post.text)
        Follow.objects.create(
            user=self.user_1,
            author=self.user,
        )
        response_2 = self.authorized_client_1.get(
            reverse('posts:follow_index')
        )
        self.assertContains(response_2, self.post.text)

    def test_authorized_client_can_unfollow(self):
        """Проверка, что авторизованный пользователь может отписываться
        от других пользователей.
        """
        Follow.objects.create(
            user=self.user_1,
            author=self.user,
        )
        self.authorized_client_1.get(
            reverse('posts:profile_unfollow', args={self.post.author.username})
        )
        self.assertFalse(
            Follow.objects.filter(
                user=self.user_1,
                author=self.user,
            ).exists()
        )

    def test_not_authorized_client_can_not_follow(self):
        """Неавторизованный пользователь не может подписаться на автора."""
        response_not_auth = self.guest_client.get(
            reverse('posts:profile_follow', args={self.post.author.username})
        )
        redirect_not_auth = \
            f'/auth/login/?next=/profile/{self.post.author.username}/follow/'
        self.assertRedirects(response_not_auth, redirect_not_auth)

    def test_new_post_is_on_the_follow_index_page(self):
        """Новая запись пользователя появляется в ленте тех,
        кто на него подписан.
        """
        self.authorized_client_1.get(
            reverse('posts:profile_follow', args={self.post.author.username})
        )
        response_user = self.authorized_client_1.get(
            reverse('posts:follow_index')
        )
        self.assertContains(response_user, self.post.text)

    def test_new_post_is_not_on_the_follow_index_page(self):
        """Новая запись пользователя не появляется в ленте тех,
        кто на него не подписан.
        """
        response_user = self.authorized_client_1.get(
            reverse('posts:follow_index')
        )
        self.assertNotContains(response_user, self.post.text)

    def test_client_can_not_follow_himself(self):
        """Пользователь не может подписаться на сосамого себя"""
        response = self.authorized_client.get(
            reverse('posts:profile_follow', args={self.post.author.username})
        )
        self.assertRedirects(response, reverse('posts:main_page'))

    def test_client_can_not_follow_two_times(self):
        """Пользователь не может два раза подписаться на одного автора"""
        Follow.objects.create(
            user=self.user_1,
            author=self.user,
        )
        self.authorized_client_1.get(
            reverse('posts:profile_follow', args={self.post.author.username})
        )
        self.assertEqual(
            len(Follow.objects.filter(
                user=self.user_1,
                author=self.user,
            )), 1
        )
