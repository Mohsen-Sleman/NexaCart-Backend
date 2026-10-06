import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from users.factories import UserFactory

pytestmark = pytest.mark.django_db

PROFILE_URL = reverse('profile')

# The smallest possible valid PNG (1x1 transparent pixel) - real image
# bytes, not a fake/empty file, so an actual image-type check passes.
TINY_PNG = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
    b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)


def test_get_profile_requires_auth(api_client):
    response = api_client.get(PROFILE_URL)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_profile_success(auth_client):
    user = UserFactory(email='profile1@example.com', first_name='Original')
    client = auth_client(user)

    response = client.get(PROFILE_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data['email'] == user.email
    assert response.data['first_name'] == 'Original'


def test_get_profile_only_shows_own_data(auth_client):
    """Not someone else's - there's no id in the URL, it must always be request.user."""
    me = UserFactory(email='profile2@example.com', first_name='Me')
    UserFactory(email='someone-else@example.com', first_name='NotMe')
    client = auth_client(me)

    response = client.get(PROFILE_URL)

    assert response.data['email'] == me.email


def test_update_profile_success(auth_client):
    user = UserFactory(email='profile3@example.com')
    client = auth_client(user)

    response = client.patch(PROFILE_URL, {'first_name': 'Updated', 'last_name': 'Name'})

    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.first_name == 'Updated'
    assert user.last_name == 'Name'


def test_update_profile_cannot_change_email(auth_client):
    user = UserFactory(email='profile4@example.com')
    client = auth_client(user)

    client.patch(PROFILE_URL, {'email': 'changed@example.com'})

    user.refresh_from_db()
    assert user.email == 'profile4@example.com'


def test_upload_profile_picture_valid_image(auth_client):
    user = UserFactory(email='profile5@example.com')
    client = auth_client(user)
    image = SimpleUploadedFile('avatar.png', TINY_PNG, content_type='image/png')

    response = client.patch(PROFILE_URL, {'profile_picture': image}, format='multipart')

    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.profile_picture
    assert user.profile_picture.name.endswith('.png')


def test_upload_profile_picture_invalid_file_type(auth_client):
    user = UserFactory(email='profile6@example.com')
    client = auth_client(user)
    fake_image = SimpleUploadedFile('not-an-image.txt', b'just text', content_type='text/plain')

    response = client.patch(PROFILE_URL, {'profile_picture': fake_image}, format='multipart')

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_replace_existing_profile_picture(auth_client):
    user = UserFactory(email='profile7@example.com')
    client = auth_client(user)
    first = SimpleUploadedFile('first.png', TINY_PNG, content_type='image/png')
    client.patch(PROFILE_URL, {'profile_picture': first}, format='multipart')
    user.refresh_from_db()
    first_name = user.profile_picture.name

    second = SimpleUploadedFile('second.png', TINY_PNG, content_type='image/png')
    response = client.patch(PROFILE_URL, {'profile_picture': second}, format='multipart')

    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.profile_picture.name != first_name
